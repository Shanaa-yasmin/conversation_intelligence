"""
RAG Engine for Compliance Detection
Uses FAISS vector database + policy embeddings for deterministic compliance checking.
No LLM policy generation.
"""

import json
import re
import os
from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path


class RAGEngine:
    """
    Retrieval-Augmented Generation for compliance detection.
    Compares conversation against enterprise-defined policies using vectors.
    """

    def __init__(self, policy_store_path: str = "policy_store"):
        self.policy_store_path = policy_store_path
        self.vectorizer = TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2))
        self.policies = {}
        self.policy_vectors = None
        self.policy_list = []
        
        self._load_policies()
        self._build_vectors()

    def _load_policies(self):
        """Load all predefined policies from JSON files."""
        policy_dir = Path(self.policy_store_path)
        
        if not policy_dir.exists():
            print(f"Warning: Policy store path {policy_dir} does not exist")
            return
        
        for policy_file in policy_dir.glob("*.json"):
            try:
                with open(policy_file, 'r') as f:
                    domain_data = json.load(f)
                    domain = domain_data.get('domain', policy_file.stem)
                    policies = domain_data.get('policies', [])
                    
                    self.policies[domain] = policies
                    for policy in policies:
                        self.policy_list.append({
                            'domain': domain,
                            'policy': policy,
                            'full_text': f"{policy['text']} {' '.join(policy.get('keywords', []))}"
                        })
            except Exception as e:
                print(f"Error loading policy file {policy_file}: {e}")

    def _build_vectors(self):
        """Build TF-IDF vectors from policy texts."""
        if not self.policy_list:
            print("Warning: No policies loaded to vectorize")
            return
        
        policy_texts = [p['full_text'] for p in self.policy_list]
        self.policy_vectors = self.vectorizer.fit_transform(policy_texts)

    def detect_violations(self, conversation: str, domain: str = None) -> Dict:
        """
        Detect policy violations in conversation.
        Returns: violations list, severity scores, policy references.
        """
        if not self.policy_list:
            return {
                'violations': [],
                'policy_references': [],
                'total_violations': 0,
                'critical_violations': 0,
                'severity_score': 0.0,
                'compliance_status': 'unknown'
            }
        
        # Filter policies by domain if specified
        relevant_policies = self._get_relevant_policies(domain)
        
        violations = []
        
        # Split conversation into chunks
        chunks = self._chunk_conversation(conversation)
        
        for chunk in chunks:
            chunk_violations = self._check_chunk_against_policies(chunk, relevant_policies)
            violations.extend(chunk_violations)
        
        # Remove duplicates, keep highest confidence
        violations = self._deduplicate_violations(violations)
        
        # Calculate aggregate metrics
        critical_count = sum(1 for v in violations if v['severity'] == 'critical')
        high_count = sum(1 for v in violations if v['severity'] == 'high')
        
        severity_score = (critical_count * 0.9 + high_count * 0.5) / max(len(violations), 1)
        
        return {
            'violations': violations,
            'policy_references': list(set(v['policy_id'] for v in violations)),
            'total_violations': len(violations),
            'critical_violations': critical_count,
            'high_violations': high_count,
            'severity_score': min(severity_score, 1.0),
            'compliance_status': 'non_compliant' if violations else 'compliant'
        }

    def _get_relevant_policies(self, domain: str = None) -> List[Dict]:
        """Get policies relevant to domain."""
        if domain and domain in self.policies:
            relevant = []
            for policy in self.policies[domain]:
                relevant.append({
                    'domain': domain,
                    'policy': policy,
                    'full_text': f"{policy['text']} {' '.join(policy.get('keywords', []))}"
                })
            return relevant
        
        return self.policy_list

    def _chunk_conversation(self, conversation: str, chunk_size: int = 200) -> List[str]:
        """Split conversation into overlapping chunks for analysis."""
        sentences = re.split(r'(?<=[.!?])\s+', conversation)
        chunks = []
        current_chunk = []
        
        for sentence in sentences:
            current_chunk.append(sentence)
            chunk_text = ' '.join(current_chunk)
            
            if len(chunk_text) >= chunk_size:
                chunks.append(chunk_text)
                # Overlap: keep last 2 sentences
                current_chunk = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk
        
        # Add remaining
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def _check_chunk_against_policies(self, chunk: str, relevant_policies: List[Dict]) -> List[Dict]:
        """Check if chunk violates any policies."""
        violations = []
        lower_chunk = chunk.lower()
        
        for policy_item in relevant_policies:
            policy = policy_item['policy']
            domain = policy_item['domain']
            
            # Check violation patterns
            if 'violation_patterns' in policy:
                for pattern in policy.get('violation_patterns', []):
                    if self._pattern_match(lower_chunk, pattern):
                        violations.append({
                            'policy_id': policy['id'],
                            'clause': policy['text'],
                            'category': policy['category'],
                            'severity': policy['severity_if_violated'],
                            'regulatory_basis': policy.get('regulatory_basis', 'N/A'),
                            'detected_phrase': self._extract_phrase(chunk, pattern),
                            'confidence': 0.98,
                            'domain': domain,
                            'remediation': self._suggest_remediation(policy['id'])
                        })
            
            # Check keywords
            for keyword in policy.get('keywords', []):
                if keyword.lower() in lower_chunk:
                    # Additional pattern-specific logic
                    if self._is_potential_violation(lower_chunk, policy, keyword):
                        if not self._violation_exists(violations, policy['id']):
                            violations.append({
                                'policy_id': policy['id'],
                                'clause': policy['text'],
                                'category': policy['category'],
                                'severity': policy['severity_if_violated'],
                                'regulatory_basis': policy.get('regulatory_basis', 'N/A'),
                                'detected_phrase': self._extract_phrase(chunk, keyword),
                                'confidence': 0.75,
                                'domain': domain,
                                'remediation': self._suggest_remediation(policy['id'])
                            })
        
        return violations

    def _pattern_match(self, text: str, pattern: str) -> bool:
        """Check if pattern exists in text."""
        pattern_lower = pattern.lower()
        # Simple substring match (can be extended to regex)
        if pattern_lower in text:
            return True
        
        # Try regex if pattern looks like regex
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except:
            pass
        
        return False

    def _extract_phrase(self, chunk: str, pattern: str) -> str:
        """Extract matched phrase from chunk."""
        pattern_lower = pattern.lower()
        chunk_lower = chunk.lower()
        
        idx = chunk_lower.find(pattern_lower)
        if idx != -1:
            # Extract context around match
            start = max(0, idx - 20)
            end = min(len(chunk), idx + len(pattern) + 30)
            return chunk[start:end].strip()
        
        return pattern

    def _is_potential_violation(self, text: str, policy: Dict, keyword: str) -> bool:
        """Determine if keyword presence constitutes violation."""
        # For certain policies, mere keyword presence is violation
        critical_keywords = ['OTP', 'CVV', 'password', 'SSN', 'Aadhaar']
        
        if keyword.upper() in critical_keywords:
            # Check if context suggests request/demand
            context_patterns = ['ask', 'request', 'tell', 'give', 'share', 'provide', 'confir']
            return any(ctx in text for ctx in context_patterns)
        
        return True

    def _violation_exists(self, violations: List[Dict], policy_id: str) -> bool:
        """Check if violation already exists in list."""
        return any(v['policy_id'] == policy_id for v in violations)

    def _deduplicate_violations(self, violations: List[Dict]) -> List[Dict]:
        """Remove duplicate violations, keep highest confidence."""
        seen = {}
        for violation in violations:
            policy_id = violation['policy_id']
            if policy_id not in seen or violation['confidence'] > seen[policy_id]['confidence']:
                seen[policy_id] = violation
        
        return list(seen.values())

    def _suggest_remediation(self, policy_id: str) -> str:
        """Provide remediation advice for violated policy."""
        remediation_map = {
            'BANK_SEC_3.2.1': 'Never request OTP verbally. Direct customer to secure channel.',
            'BANK_SEC_3.2.2': 'Use tokenized payment processing. Never collect raw CVV.',
            'BANK_KYC_4.1.1': 'Complete all KYC steps before account activation.',
            'BANK_DISC_5.1.1': 'Always provide mandatory disclaimer before financial discussion.',
            'BANK_DATA_6.1.1': 'Use secure SMS/email for sensitive data. Never verbally confirm.',
            'BANK_LOAN_7.1.1': 'Only state that approval is subject to bank assessment.',
            'TELECOM_ROAM_1.1.1': 'Provide written roaming cost estimate before activation.',
            'TELECOM_SLA_2.1.1': 'Describe SLA as "best effort" subject to network conditions.',
        }
        
        return remediation_map.get(policy_id, 'Review policy compliance procedure.')

    def detect_critical_data_exposure(self, conversation: str) -> Dict:
        """
        Detect exposure of critical data (OTP, CVV, SSN, etc).
        Load patterns from critical_data_store.
        """
        exposure_results = {
            'exposed_data_types': [],
            'exposures': [],
            'risk_level': 'safe',
            'total_exposures': 0
        }
        
        # Load critical data patterns
        critical_data_path = Path("critical_data_store") / "sensitive_patterns.json"
        if not critical_data_path.exists():
            return exposure_results
        
        try:
            with open(critical_data_path, 'r') as f:
                critical_data_config = json.load(f)
        except:
            return exposure_results
        
        lower_convo = conversation.lower()
        
        for data_type in critical_data_config.get('critical_data_types', []):
            data_name = data_type['type']
            patterns = data_type.get('patterns', [])
            severity = data_type.get('severity', 'high')
            
            for pattern in patterns:
                if self._pattern_match(lower_convo, pattern):
                    exposure_results['exposed_data_types'].append(data_name)
                    exposure_results['exposures'].append({
                        'data_type': data_name,
                        'description': data_type['description'],
                        'severity': severity,
                        'pattern_matched': pattern,
                        'remediation': f'Review {data_name} handling procedures and re-train agent.'
                    })
        
        exposure_results['total_exposures'] = len(exposure_results['exposures'])
        
        if exposure_results['total_exposures'] >= 2:
            exposure_results['risk_level'] = 'critical'
        elif exposure_results['total_exposures'] >= 1:
            exposure_results['risk_level'] = 'high'
        
        return exposure_results

    def get_policy_coverage(self, domain: str = None) -> Dict:
        """Get overview of policy coverage."""
        if domain and domain in self.policies:
            policies = self.policies[domain]
            return {
                'domain': domain,
                'policy_count': len(policies),
                'categories': list(set(p['category'] for p in policies)),
                'critical_policies': sum(1 for p in policies if p['severity_if_violated'] == 'critical')
            }
        
        return {
            'total_domains': len(self.policies),
            'total_policies': len(self.policy_list),
            'domains': list(self.policies.keys())
        }
