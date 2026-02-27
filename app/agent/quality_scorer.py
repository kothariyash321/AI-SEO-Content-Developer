"""Quality scoring for SEO constraints."""
import re

from app.api.schemas import (
    ArticleOutput,
    QualityReport,
    QualityCheck,
)


class QualityScorer:
    """Score article quality based on SEO constraints."""
    
    def score(self, article_output: ArticleOutput, target_word_count: int = 1500) -> QualityReport:
        """Score the article and return quality report."""
        checks = []
        total_points = 0
        max_total = 100
        
        # Check 1: Primary keyword in H1
        h1_section = next(
            (s for s in article_output.sections if s.heading_level == "H1"),
            None
        )
        if h1_section:
            keyword_in_h1 = article_output.seo_metadata.primary_keyword.lower() in h1_section.heading_text.lower()
            points = 15 if keyword_in_h1 else 0
            checks.append(QualityCheck(
                check_name="Primary keyword in H1",
                passed=keyword_in_h1,
                points=points,
                max_points=15,
                details="Found" if keyword_in_h1 else "Missing",
            ))
            total_points += points
        else:
            checks.append(QualityCheck(
                check_name="Primary keyword in H1",
                passed=False,
                points=0,
                max_points=15,
                details="No H1 found",
            ))
        
        # Check 2: Primary keyword in first 100 words
        if article_output.sections:
            intro_text = " ".join(
                s.content for s in article_output.sections[:2]
            )[:500]  # First 500 chars
            words = re.findall(r'\b\w+\b', intro_text)
            first_100_words = " ".join(words[:100]).lower()
            keyword_in_intro = article_output.seo_metadata.primary_keyword.lower() in first_100_words
            points = 10 if keyword_in_intro else 0
            checks.append(QualityCheck(
                check_name="Primary keyword in first 100 words",
                passed=keyword_in_intro,
                points=points,
                max_points=10,
                details="Found" if keyword_in_intro else "Missing",
            ))
            total_points += points
        
        # Check 3: Meta title length (50-60 chars)
        title_len = len(article_output.seo_metadata.title_tag)
        title_valid = 50 <= title_len <= 60
        points = 10 if title_valid else 0
        checks.append(QualityCheck(
            check_name="Meta title length (50-60 chars)",
            passed=title_valid,
            points=points,
            max_points=10,
            details=f"{title_len} characters",
        ))
        total_points += points
        
        # Check 4: Meta description length (150-160 chars)
        desc_len = len(article_output.seo_metadata.meta_description)
        desc_valid = 150 <= desc_len <= 160
        points = 10 if desc_valid else 0
        checks.append(QualityCheck(
            check_name="Meta description length (150-160 chars)",
            passed=desc_valid,
            points=points,
            max_points=10,
            details=f"{desc_len} characters",
        ))
        total_points += points
        
        # Check 5: Heading hierarchy valid
        h1_count = sum(1 for s in article_output.sections if s.heading_level == "H1")
        hierarchy_valid = h1_count == 1
        
        # Check H2/H3 nesting (simplified: just check H1 count for now)
        points = 15 if hierarchy_valid else 0
        checks.append(QualityCheck(
            check_name="Heading hierarchy valid",
            passed=hierarchy_valid,
            points=points,
            max_points=15,
            details=f"{h1_count} H1(s) found",
        ))
        total_points += points
        
        # Check 6: Word count within 10% of target
        word_count_diff = abs(article_output.total_word_count - target_word_count) / target_word_count
        word_count_valid = word_count_diff <= 0.10
        points = 10 if word_count_valid else 0
        checks.append(QualityCheck(
            check_name="Word count within 10% of target",
            passed=word_count_valid,
            points=points,
            max_points=10,
            details=f"{article_output.total_word_count} words (target: {target_word_count})",
        ))
        total_points += points
        
        # Check 7: Secondary keyword coverage (>=60%) - IMPROVED matching
        if article_output.seo_metadata.secondary_keywords:
            article_text = " ".join(s.content for s in article_output.sections).lower()
            
            # Normalize article text: remove common stop words that might interfere
            # and create a normalized version for matching
            normalized_article = article_text
            
            keywords_present = 0
            matched_keywords = []
            unmatched_keywords = []
            
            for kw in article_output.seo_metadata.secondary_keywords:
                kw_lower = kw.lower()
                
                # Try exact match first
                if kw_lower in normalized_article:
                    keywords_present += 1
                    matched_keywords.append(kw)
                    continue
                
                # Try normalized matching: remove common words like "in", "for", "the"
                # and check if key terms appear
                kw_words = [w for w in kw_lower.split() if w not in ['in', 'for', 'the', 'a', 'an', 'and', 'or']]
                if len(kw_words) >= 2:
                    # Check if at least 2 key words appear together (within reasonable distance)
                    # For phrases like "machine learning diagnostics", check if both "machine learning" and "diagnostics" appear
                    key_phrase = " ".join(kw_words[:2])  # First two significant words
                    remaining_words = kw_words[2:] if len(kw_words) > 2 else []
                    
                    if key_phrase in normalized_article:
                        # Check if remaining words also appear (for longer phrases)
                        if not remaining_words or all(word in normalized_article for word in remaining_words):
                            keywords_present += 1
                            matched_keywords.append(kw)
                            continue
                
                # Try substring matching: check if significant parts of the keyword appear
                # e.g., "machine learning diagnostics" should match "machine learning for diagnostics"
                if len(kw_words) >= 2:
                    # Check if all significant words appear (in any order, but close together)
                    significant_words = [w for w in kw_words if len(w) > 3]  # Words longer than 3 chars
                    if significant_words and all(word in normalized_article for word in significant_words):
                        # Verify they appear relatively close (within 50 words of each other)
                        # Simple heuristic: if all key words are in the text, consider it matched
                        keywords_present += 1
                        matched_keywords.append(kw)
                        continue
                
                unmatched_keywords.append(kw)
            
            coverage = keywords_present / len(article_output.seo_metadata.secondary_keywords)
            coverage_valid = coverage >= 0.60
            points = 15 if coverage_valid else int(15 * coverage)
            
            details_str = f"{keywords_present}/{len(article_output.seo_metadata.secondary_keywords)} keywords found ({coverage*100:.1f}%)"
            if matched_keywords:
                details_str += f" - Matched: {', '.join(matched_keywords[:3])}"
            if unmatched_keywords:
                details_str += f" - Unmatched: {', '.join(unmatched_keywords[:3])}"
            
            checks.append(QualityCheck(
                check_name="Secondary keyword coverage (>=60%)",
                passed=coverage_valid,
                points=points,
                max_points=15,
                details=details_str,
            ))
            total_points += points
        else:
            checks.append(QualityCheck(
                check_name="Secondary keyword coverage (>=60%)",
                passed=False,
                points=0,
                max_points=15,
                details="No secondary keywords",
            ))
        
        # Check 8: Internal links present (3-5)
        internal_link_count = len(article_output.internal_links)
        internal_links_valid = 3 <= internal_link_count <= 5
        points = 10 if internal_links_valid else (5 if internal_link_count > 0 else 0)
        checks.append(QualityCheck(
            check_name="Internal links present (3-5)",
            passed=internal_links_valid,
            points=points,
            max_points=10,
            details=f"{internal_link_count} internal links",
        ))
        total_points += points
        
        # Check 9: External references present (2-4)
        external_ref_count = len(article_output.external_references)
        external_refs_valid = 2 <= external_ref_count <= 4
        points = 5 if external_refs_valid else (2 if external_ref_count > 0 else 0)
        checks.append(QualityCheck(
            check_name="External references present (2-4)",
            passed=external_refs_valid,
            points=points,
            max_points=5,
            details=f"{external_ref_count} external references",
        ))
        total_points += points
        
        # Check 10: Phrase repetition / Keyword stuffing (IMPROVED)
        article_text = " ".join(s.content for s in article_output.sections).lower()
        total_words = len(re.findall(r'\b\w+\b', article_text))
        
        # Check for excessive repetition of secondary keywords
        max_repetitions_per_100_words = 1.5  # Stricter: max 1.5 times per 100 words
        phrase_repetition_issues = []
        
        for keyword in article_output.seo_metadata.secondary_keywords:
            keyword_lower = keyword.lower()
            # Count occurrences of the full phrase
            occurrences = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', article_text))
            occurrences_per_100_words = (occurrences / total_words) * 100 if total_words > 0 else 0
            
            # If phrase appears more than 1.5 times per 100 words, flag it
            if occurrences_per_100_words > max_repetitions_per_100_words:
                phrase_repetition_issues.append(f"{keyword} ({occurrences}x, {occurrences_per_100_words:.1f}/100 words)")
        
        # Check for common robotic phrases
        robotic_phrases = [
            "real-world applications",
            "expert insights",
            "ai strategies",
            "healthcare tools",
            "ai solutions",
        ]
        
        for phrase in robotic_phrases:
            phrase_lower = phrase.lower()
            occurrences = len(re.findall(r'\b' + re.escape(phrase_lower) + r'\b', article_text))
            occurrences_per_100_words = (occurrences / total_words) * 100 if total_words > 0 else 0
            if occurrences_per_100_words > max_repetitions_per_100_words:
                phrase_repetition_issues.append(f"{phrase} ({occurrences}x, {occurrences_per_100_words:.1f}/100 words)")
        
        # Score: Stricter thresholds
        phrase_repetition_valid = len(phrase_repetition_issues) == 0
        if phrase_repetition_valid:
            points = 10
        elif len(phrase_repetition_issues) <= 2:
            points = 5
        elif len(phrase_repetition_issues) <= 4:
            points = 2
        else:
            points = 0
        
        checks.append(QualityCheck(
            check_name="Phrase repetition / Keyword stuffing",
            passed=phrase_repetition_valid,
            points=points,
            max_points=10,
            details=f"{len(phrase_repetition_issues)} overused phrases: {', '.join(phrase_repetition_issues[:5])}" if phrase_repetition_issues else "No excessive repetition",
        ))
        total_points += points
        
        # Update max_total
        max_total = 110  # Added new check
        
        passed_checks = sum(1 for c in checks if c.passed)
        failed_checks = len(checks) - passed_checks
        
        # FIX: Sum earned points, not max_points
        earned_points = sum(c.points for c in checks)
        
        return QualityReport(
            total=min(earned_points, 100),  # Cap at 100, use earned points
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            details=checks,
        )
