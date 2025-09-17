# src/mcp/tools/video_content.py
"""
ContentAgent for batch LLM summarization with structured output optimization
"""

import asyncio
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from src.mcp.tools.video_transcription import TranscriptSegment
from src.common.jsonlog import jlog

log = logging.getLogger("video_content")


class BulletPoint(BaseModel):
    """Structured bullet point for slides"""
    timestamp: str = Field(pattern=r"\d{2}:\d{2}")  # MM:SS format
    text: str = Field(max_length=150)  # Allow longer text for better context
    confidence: float = Field(ge=0.0, le=1.0)
    duration: float = Field(ge=0.0)  # Duration this bullet should be shown


class VideoSummary(BaseModel):
    """Structured video summary output"""
    bullet_points: List[BulletPoint] = Field(min_items=3)  # Removed max_items=10 for Phase 2
    main_themes: List[str] = Field(max_items=3)
    total_duration: str = Field(pattern=r"\d{2}:\d{2}")
    language: str = "en"
    summary_confidence: float = Field(ge=0.0, le=1.0)


@dataclass
class ContentResult:
    """Result of content processing"""
    success: bool
    summary: Optional[VideoSummary]
    processing_time: float
    tokens_used: int
    model_used: str
    cache_hit: bool
    error: Optional[str] = None


class ContentAgent:
    """Agent for LLM-based content summarization with token optimization"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.cache = {}  # Simple in-memory cache for demo
        self.demo_mode = True  # Optimize for speed over perfection
    
    async def batch_summarize(self, segments: List[TranscriptSegment], 
                            max_bullets: int = 5) -> ContentResult:
        """
        Batch process transcript segments into structured bullet points
        
        Args:
            segments: List of transcript segments from Whisper
            max_bullets: Maximum number of bullet points (3-5 for demo)
            
        Returns:
            ContentResult with structured summary
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="content_summarization_start",
             job_id=self.job_id,
             segments_count=len(segments),
             max_bullets=max_bullets,
             demo_mode=self.demo_mode)
        
        try:
            # Consolidate segments into single text for processing
            consolidated_text = self._consolidate_segments(segments)
            
            # Check cache for similar content
            cache_key = self._get_cache_key(consolidated_text, max_bullets)
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                processing_time = time.time() - start_time
                
                jlog(log, logging.INFO,
                     event="content_cache_hit",
                     job_id=self.job_id,
                     cache_key=cache_key[:16],
                     processing_time=processing_time)
                
                return ContentResult(
                    success=True,
                    summary=cached_result,
                    processing_time=processing_time,
                    tokens_used=0,  # No tokens used for cache hit
                    model_used="cached",
                    cache_hit=True
                )
            
            # Create efficient batch prompt
            prompt = self._create_batch_prompt(consolidated_text, segments, max_bullets)
            
            # Process with LLM (structured output)
            summary = await self._process_with_llm(prompt, consolidated_text, segments, max_bullets)
            
            # Cache the result
            self.cache[cache_key] = summary
            
            processing_time = time.time() - start_time
            
            result = ContentResult(
                success=True,
                summary=summary,
                processing_time=processing_time,
                tokens_used=len(prompt.split()) + len(str(summary.dict())),  # Rough estimate
                model_used="simulated-gemini",  # Would be actual model in production
                cache_hit=False
            )
            
            jlog(log, logging.INFO,
                 event="content_summarization_success",
                 job_id=self.job_id,
                 processing_time=round(processing_time, 2),
                 bullets_generated=len(summary.bullet_points),
                 tokens_estimated=result.tokens_used,
                 themes_count=len(summary.main_themes))
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Content summarization failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="content_summarization_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 processing_time=round(processing_time, 2))
            
            return ContentResult(
                success=False,
                summary=None,
                processing_time=processing_time,
                tokens_used=0,
                model_used="failed",
                cache_hit=False,
                error=error_msg
            )
    
    def _consolidate_segments(self, segments: List[TranscriptSegment]) -> str:
        """Consolidate transcript segments into single text"""
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time)
        
        # Create consolidated text with timing markers
        consolidated = []
        for segment in sorted_segments:
            # Format: [MM:SS] text
            timestamp = f"[{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}]"
            consolidated.append(f"{timestamp} {segment.text}")
        
        text = " ".join(consolidated)
        
        jlog(log, logging.INFO,
             event="segments_consolidated",
             job_id=self.job_id,
             original_segments=len(segments),
             consolidated_length=len(text))
        
        return text
    
    def _get_cache_key(self, text: str, max_bullets: int) -> str:
        """Generate cache key for content"""
        content = f"{text[:500]}:{max_bullets}"  # Use first 500 chars + config
        return hashlib.md5(content.encode()).hexdigest()
    
    def _create_batch_prompt(self, consolidated_text: str, segments: List[TranscriptSegment], 
                           max_bullets: int) -> str:
        """Create optimized prompt for batch processing"""
        
        # Compress text if too long (token optimization)
        if len(consolidated_text) > 2000:
            consolidated_text = consolidated_text[:2000] + "..."
        
        # Calculate total duration
        total_duration = max((s.end_time for s in segments), default=0)
        duration_str = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}"
        
        prompt = f"""
        Convert this video transcript into {max_bullets} key bullet points for a presentation slide.
        
        Video Duration: {duration_str}
        Transcript with timestamps: {consolidated_text}
        
        Requirements:
        - {max_bullets} bullet points maximum
        - Each bullet: max 25 words, clear and actionable
        - Include timestamp when each point should appear (MM:SS format)
        - Focus on main insights, decisions, or takeaways
        - Professional business language
        - Show complete thoughts rather than truncated phrases
        
        Return structured JSON matching this format exactly:
        {{
            "bullet_points": [
                {{"timestamp": "00:30", "text": "Key insight here", "confidence": 0.9, "duration": 20.0}},
                ...
            ],
            "main_themes": ["theme1", "theme2", "theme3"],
            "total_duration": "{duration_str}",
            "language": "en",
            "summary_confidence": 0.8
        }}
        """
        
        return prompt.strip()
    
    async def _process_with_llm(self, prompt: str, consolidated_text: str,
                              segments: List[TranscriptSegment], max_bullets: int = 5) -> VideoSummary:
        """Process with actual LLM to generate bullet point summaries"""

        try:
            # Use the existing LLM infrastructure
            from src.mcp.tools.llm import llm_summarize_tool

            jlog(log, logging.INFO,
                 event="llm_processing_start",
                 job_id=self.job_id,
                 prompt_length=len(prompt))

            # Prepare LLM parameters according to SummarizeParams schema
            llm_params = {
                "report_text": consolidated_text[:60000],  # Limit to max length
                "max_sections": min(len(segments), max_bullets),
                "max_script_chars": 700
            }

            # Get LLM response
            llm_result = llm_summarize_tool(llm_params)

            if not isinstance(llm_result, dict) or "sections" not in llm_result:
                raise ValueError("LLM response is not a dict or missing 'sections'")

            slides_data = llm_result["sections"]
            bullet_points = []
            bullet_index = 0
            for i, slide in enumerate(slides_data[:max_bullets]):
                if bullet_index >= max_bullets:
                    break
                for bullet_text in slide.get("bullets", []):
                    if bullet_index >= max_bullets:
                        break
                    timestamp = f"{(bullet_index * 20) // 60:02d}:{(bullet_index * 20) % 60:02d}"
                    bullet_points.append({
                        "timestamp": timestamp,
                        "text": bullet_text,
                        "confidence": 0.85,  # Higher confidence for LLM
                        "duration": 20.0
                    })
                    bullet_index += 1

            if len(bullet_points) < 3:
                raise ValueError(f"LLM generated {len(bullet_points)} bullets, but need at least 3.")

            total_duration_secs = len(bullet_points) * 20
            llm_response = {
                "bullet_points": bullet_points,
                "main_themes": [slide.get("title", f"Theme {i+1}") for i, slide in enumerate(slides_data[:3])],
                "total_duration": f"{total_duration_secs // 60:02d}:{total_duration_secs % 60:02d}",
                "language": "en",
                "summary_confidence": 0.85
            }

            # Parse the structured response
            summary = VideoSummary(**llm_response)

            jlog(log, logging.INFO,
                 event="llm_processing_success",
                 job_id=self.job_id,
                 bullets_generated=len(summary.bullet_points))

            return summary

        except (ValueError, Exception) as e:
            jlog(log, logging.WARNING,
                 event="llm_processing_fallback",
                 job_id=self.job_id,
                 error=f"LLM processing failed, falling back. Reason: {str(e)}")

            # Fallback to improved simulated summary
            summary = self._create_intelligent_summary(consolidated_text, segments, max_bullets)

            jlog(log, logging.INFO,
                 event="llm_processing_fallback_complete",
                 job_id=self.job_id,
                 response_bullets=len(summary.bullet_points))

            return summary
    
    def _create_intelligent_summary(self, text: str, segments: List[TranscriptSegment], max_bullets: int = 5) -> VideoSummary:
        """Create intelligent simulated summary based on transcript content"""

        # Calculate total video duration
        total_duration = max((s.end_time for s in segments), default=0)

        # Use content-aware sectional assignment (Phase 1 implementation)
        bullet_points = self._assign_bullets_by_content_sections(segments, total_duration, max_bullets)

        # Extract themes from the generated bullets
        themes = self._extract_themes_from_bullets(bullet_points)

        jlog(log, logging.INFO,
             event="content_aware_bullet_assignment",
             job_id=self.job_id,
             total_duration=total_duration,
             bullets_generated=len(bullet_points),
             assignment_method="sectional_content_aware")

        # Create summary with bullet_points and themes
        duration_str = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}"

        # Calculate overall confidence
        if bullet_points:
            avg_confidence = sum(bp.confidence for bp in bullet_points) / len(bullet_points)
        else:
            avg_confidence = 0.5

        return VideoSummary(
            bullet_points=bullet_points,
            main_themes=themes,
            total_duration=duration_str,
            language="en",
            summary_confidence=avg_confidence
        )

    def _assign_bullets_by_content_sections(self, segments: List[TranscriptSegment],
                                          video_duration: float, bullet_count: int) -> List[BulletPoint]:
        """
        Phase 1: Content-Aware Sectional Assignment
        Divide video into equal sections and assign bullets based on section content
        """
        if not segments or bullet_count <= 0:
            return []

        # Ensure minimum bullet count
        bullet_count = max(3, bullet_count)

        # Calculate section duration
        section_duration = video_duration / bullet_count
        bullets = []

        jlog(log, logging.INFO,
             event="sectional_assignment_start",
             job_id=self.job_id,
             video_duration=video_duration,
             bullet_count=bullet_count,
             section_duration=section_duration)

        for i in range(bullet_count):
            section_start = i * section_duration
            section_end = min((i + 1) * section_duration, video_duration)
            section_midpoint = section_start + (section_duration / 2)

            # Get transcript segments that fall within this time section
            section_segments = [seg for seg in segments
                              if section_start <= seg.start_time < section_end]

            if section_segments:
                # Summarize content specifically for this section
                section_content = self._summarize_section_content(section_segments)

                # Calculate confidence based on content density
                confidence = min(0.95, 0.7 + (len(section_segments) * 0.05))

                # Calculate duration (80% of section duration, max 45s)
                duration = min(45.0, max(15.0, section_duration * 0.8))

                bullet = BulletPoint(
                    timestamp=self._format_timestamp(section_midpoint),
                    text=section_content,
                    confidence=confidence,
                    duration=duration
                )
                bullets.append(bullet)

                jlog(log, logging.INFO,
                     event="section_bullet_created",
                     job_id=self.job_id,
                     section_index=i+1,
                     section_start=section_start,
                     section_end=section_end,
                     midpoint=section_midpoint,
                     segments_in_section=len(section_segments),
                     content_preview=section_content[:50] + "..." if len(section_content) > 50 else section_content)
            else:
                # No content in this section, create placeholder
                placeholder_content = f"Key point {i+1} from presentation"
                bullet = BulletPoint(
                    timestamp=self._format_timestamp(section_midpoint),
                    text=placeholder_content,
                    confidence=0.5,
                    duration=min(30.0, section_duration * 0.8)
                )
                bullets.append(bullet)

                jlog(log, logging.WARNING,
                     event="section_bullet_placeholder",
                     job_id=self.job_id,
                     section_index=i+1,
                     reason="no_transcript_segments_in_section")

        return bullets

    def _summarize_section_content(self, section_segments: List[TranscriptSegment]) -> str:
        """
        Create a concise bullet point summary from transcript segments in a specific time section
        """
        if not section_segments:
            return "Key presentation point"

        # Combine all text from this section
        combined_text = " ".join(seg.text.strip() for seg in section_segments)

        # Enhanced keyword detection for business presentations
        business_keywords = [
            "objective", "goal", "target", "result", "achievement", "challenge",
            "solution", "strategy", "plan", "proposal", "recommendation",
            "data", "analysis", "insight", "conclusion", "next steps",
            "implementation", "outcome", "decision", "action", "priority"
        ]

        # Find relevant keywords in this section
        found_keywords = [kw for kw in business_keywords if kw in combined_text.lower()]

        # Use keyword analysis to create focused summary
        return self._create_focused_summary(combined_text, found_keywords)

    def _create_focused_summary(self, text: str, keywords: List[str]) -> str:
        """
        Create a focused summary based on content and detected keywords
        """
        # Clean and prepare text
        text = text.strip()

        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        if not sentences:
            return text[:100] + "..." if len(text) > 100 else text

        # Find the most keyword-rich sentence
        best_sentence = sentences[0]
        max_keyword_count = 0

        for sentence in sentences:
            keyword_count = sum(1 for kw in keywords if kw in sentence.lower())
            if keyword_count > max_keyword_count:
                max_keyword_count = keyword_count
                best_sentence = sentence

        # If the best sentence is too short, combine with next relevant sentence
        if len(best_sentence) < 40 and len(sentences) > 1:
            for sentence in sentences[1:]:
                combined = f"{best_sentence}. {sentence}"
                if len(combined) <= 120:  # Keep under reasonable length
                    best_sentence = combined
                    break

        # Ensure reasonable length
        if len(best_sentence) > 140:
            best_sentence = best_sentence[:137] + "..."

        return best_sentence

    def _extract_themes_from_bullets(self, bullet_points: List[BulletPoint]) -> List[str]:
        """
        Extract main themes from the generated bullet points
        """
        if not bullet_points:
            return ["Presentation", "Content", "Summary"]

        # Combine all bullet text
        all_text = " ".join(bp.text for bp in bullet_points).lower()

        # Common presentation themes
        theme_keywords = {
            "Strategy": ["strategy", "strategic", "plan", "planning", "approach"],
            "Results": ["result", "outcome", "achievement", "success", "performance"],
            "Analysis": ["analysis", "data", "insight", "finding", "research"],
            "Implementation": ["implement", "execution", "deploy", "launch", "action"],
            "Goals": ["goal", "objective", "target", "aim", "purpose"],
            "Challenges": ["challenge", "problem", "issue", "concern", "obstacle"],
            "Solutions": ["solution", "resolve", "fix", "address", "answer"],
            "Innovation": ["innovation", "new", "innovative", "creative", "novel"],
            "Growth": ["growth", "increase", "expand", "scale", "develop"],
            "Quality": ["quality", "improvement", "enhance", "optimize", "better"]
        }

        # Score themes based on keyword presence
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(1 for kw in keywords if kw in all_text)
            if score > 0:
                theme_scores[theme] = score

        # Return top 3 themes, or defaults if none found
        if theme_scores:
            sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
            return [theme for theme, _ in sorted_themes[:3]]
        else:
            return ["Business", "Presentation", "Overview"]

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _summarize_segment_text(self, text: str, keywords: List[str]) -> str:
        """Convert raw transcript text into concise but complete bullet point summary"""

        # Clean up the text
        text = text.strip()

        # Don't truncate - use complete sentences
        # Find complete sentences first
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        if not sentences:
            # If no sentences, use the full text
            return text

        # Take the first complete sentence as the main point
        main_sentence = sentences[0]

        # If it's too short, add the second sentence
        if len(main_sentence) < 30 and len(sentences) > 1:
            main_sentence = f"{main_sentence}. {sentences[1]}"

        # Basic patterns to identify key information types
        patterns = {
            "goal": ["goal", "objective", "aim", "target", "purpose", "want to", "trying to"],
            "result": ["result", "outcome", "achievement", "success", "improvement", "shows", "demonstrates"],
            "data": ["data", "numbers", "percent", "analysis", "statistics", "shows that", "indicates"],
            "action": ["implement", "execute", "deploy", "launch", "start", "will", "going to"],
            "recommendation": ["recommend", "suggest", "should", "need to", "must", "propose"],
            "challenge": ["challenge", "problem", "issue", "difficulty", "concern"],
            "solution": ["solution", "fix", "resolve", "address", "solve", "answer"],
        }

        # Enhance the sentence based on detected patterns and keywords
        enhanced_sentence = main_sentence

        # Look for patterns that indicate the type of information
        text_lower = main_sentence.lower()
        for pattern_type, pattern_words in patterns.items():
            if any(word in text_lower for word in pattern_words):
                # Pattern found - this gives us context for the bullet type
                break

        # Ensure we don't exceed reasonable length
        if len(enhanced_sentence) > 140:
            enhanced_sentence = enhanced_sentence[:137] + "..."

        return enhanced_sentence


if __name__ == "__main__":
    # Test ContentAgent with new sectional assignment
    async def test_content_agent():
        print("Testing ContentAgent with new sectional assignment...")

        # Create mock transcript segments for testing
        mock_segments = [
            TranscriptSegment(0.0, 10.0, "Welcome to our project presentation on sales automation.", 0.9),
            TranscriptSegment(10.0, 25.0, "Our goal is to increase sales efficiency by 40% through AI integration.", 0.9),
            TranscriptSegment(25.0, 45.0, "The data shows significant improvement in lead conversion rates.", 0.8),
            TranscriptSegment(45.0, 65.0, "Implementation strategy involves three key phases for deployment.", 0.9),
            TranscriptSegment(65.0, 80.0, "Next steps include team training and system rollout schedule.", 0.8),
        ]

        # Test with job configuration
        test_job_id = "test-sectional-assignment"
        agent = ContentAgent(test_job_id)

        # Test sectional assignment with 5 bullets
        result = await agent.batch_summarize(mock_segments, max_bullets=5)

        print(f"Processing: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Bullets generated: {len(result.summary.bullet_points) if result.summary else 0}")
        print(f"Cache hit: {result.cache_hit}")

        if result.summary:
            print(f"\\nBullet Points ({len(result.summary.bullet_points)}):")
            for i, bullet in enumerate(result.summary.bullet_points, 1):
                print(f"  {i}. [{bullet.timestamp}] {bullet.text}")
                print(f"     Confidence: {bullet.confidence:.2f}, Duration: {bullet.duration}s")

            print(f"\\nThemes: {result.summary.main_themes}")
            print(f"Total Duration: {result.summary.total_duration}")
            print(f"Summary Confidence: {result.summary.summary_confidence:.2f}")

        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(test_content_agent())
