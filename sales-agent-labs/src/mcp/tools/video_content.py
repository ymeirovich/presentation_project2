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
    bullet_points: List[BulletPoint] = Field(min_items=3, max_items=5)
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
            summary = await self._process_with_llm(prompt, consolidated_text, segments)
            
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
                              segments: List[TranscriptSegment]) -> VideoSummary:
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
                "max_sections": min(len(segments), 5),
                "max_script_chars": 700
            }

            # Get LLM response
            llm_result = llm_summarize_tool(llm_params)

            if not isinstance(llm_result, dict) or "sections" not in llm_result:
                raise ValueError("LLM response is not a dict or missing 'sections'")

            slides_data = llm_result["sections"]
            bullet_points = []
            bullet_index = 0
            for i, slide in enumerate(slides_data[:5]):
                if bullet_index >= 5:
                    break
                for bullet_text in slide.get("bullets", []):
                    if bullet_index >= 5:
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
            summary = self._create_intelligent_summary(consolidated_text, segments)

            jlog(log, logging.INFO,
                 event="llm_processing_fallback_complete",
                 job_id=self.job_id,
                 response_bullets=len(summary.bullet_points))

            return summary
    
    def _create_intelligent_summary(self, text: str, segments: List[TranscriptSegment]) -> VideoSummary:
        """Create intelligent simulated summary based on transcript content"""
        
        # Analyze segments for key content
        bullet_points = []
        themes = []
        
        # Simple keyword-based extraction for demo
        keywords_found = []
        
        # Look for business/presentation keywords
        business_keywords = [
            "project", "goal", "target", "result", "achievement", "challenge", 
            "solution", "strategy", "plan", "proposal", "recommendation",
            "data", "analysis", "insight", "conclusion", "next steps"
        ]
        
        # Extract segments with business keywords
        important_segments = []
        for segment in segments:
            text_lower = segment.text.lower()
            segment_keywords = [kw for kw in business_keywords if kw in text_lower]
            if segment_keywords:
                important_segments.append((segment, segment_keywords))
                keywords_found.extend(segment_keywords)
        
        # Create bullet points from important segments (max 5)
        for i, (segment, keywords) in enumerate(important_segments[:5]):
            # Create summarized bullet text instead of raw transcript
            bullet_text = self._summarize_segment_text(segment.text.strip(), keywords)
            if len(bullet_text) > 140:
                bullet_text = bullet_text[:137] + "..."
            
            # Format timestamp
            timestamp = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
            
            # Calculate confidence based on keywords and position
            confidence = min(0.95, 0.7 + (len(keywords) * 0.1))
            
            # Duration to show this bullet (until next one)
            if i < len(important_segments) - 1:
                next_segment = important_segments[i + 1][0]
                duration = next_segment.start_time - segment.start_time
            else:
                duration = 30.0  # Default duration
            
            bullet_points.append(BulletPoint(
                timestamp=timestamp,
                text=bullet_text,
                confidence=confidence,
                duration=max(15.0, min(45.0, duration))  # Clamp between 15-45s
            ))
        
        # Ensure we have at least 3 bullet points
        if len(bullet_points) < 3 and segments:
            # Take evenly distributed segments to fill remaining slots
            remaining_needed = 3 - len(bullet_points)
            used_segments = set()
            
            # Mark segments already used for bullet points
            for bp in bullet_points:
                bp_time = int(bp.timestamp.split(':')[0]) * 60 + int(bp.timestamp.split(':')[1])
                for i, seg in enumerate(segments):
                    if abs(seg.start_time - bp_time) < 5:  # Within 5 seconds
                        used_segments.add(i)
                        break
            
            # Find evenly distributed unused segments
            available_segments = [(i, seg) for i, seg in enumerate(segments) if i not in used_segments]
            
            if available_segments:
                # Take evenly distributed segments
                step = max(1, len(available_segments) // remaining_needed)
                for i in range(0, min(len(available_segments), remaining_needed * step), step):
                    idx, segment = available_segments[i]
                    # Create summarized bullet text instead of raw transcript
                    bullet_text = self._summarize_segment_text(segment.text.strip(), [])
                    if len(bullet_text) > 140:
                        bullet_text = bullet_text[:137] + "..."
                    
                    timestamp = f"{int(segment.start_time//60):02d}:{int(segment.start_time%60):02d}"
                    
                    bullet_points.append(BulletPoint(
                        timestamp=timestamp,
                        text=bullet_text,
                        confidence=0.6,  # Lower confidence for generic extraction
                        duration=30.0
                    ))
                    
                    if len(bullet_points) >= 5:  # Don't exceed max
                        break
        
        # Extract themes from keywords
        theme_keywords = list(set(keywords_found))[:3]
        if not theme_keywords:
            themes = ["Key Discussion Points", "Main Insights", "Action Items"]
        else:
            themes = [kw.title() for kw in theme_keywords[:3]]
        
        # Calculate total duration
        total_duration = max((s.end_time for s in segments), default=0)
        duration_str = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}"
        
        # Calculate overall confidence
        if bullet_points:
            avg_confidence = sum(bp.confidence for bp in bullet_points) / len(bullet_points)
        else:
            avg_confidence = 0.5
        
        return VideoSummary(
            bullet_points=bullet_points[:5],  # Max 5
            main_themes=themes,
            total_duration=duration_str,
            language="en",
            summary_confidence=avg_confidence
        )
    
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
            "intro": ["meet", "introduce", "presenting", "welcome", "today"]
        }
        
        # Identify the type of content
        text_lower = main_sentence.lower()
        content_type = None
        
        for category, pattern_words in patterns.items():
            if any(word in text_lower for word in pattern_words):
                content_type = category
                break
        
        # Clean up and ensure complete sentence
        summary = main_sentence
        
        # Ensure it ends properly
        if not summary.endswith(('.', '!', '?')):
            summary += '.'
        
        # Add context based on content type for clarity
        if content_type == "goal" and not summary.lower().startswith(("goal", "objective", "our goal")):
            summary = f"Goal: {summary}"
        elif content_type == "result" and not summary.lower().startswith(("result", "outcome", "data shows")):
            summary = f"Result: {summary}"
        elif content_type == "recommendation" and not summary.lower().startswith(("recommend", "suggestion")):
            summary = f"Recommendation: {summary}"
        elif content_type == "intro" and summary.lower().startswith("meet"):
            # Keep intro statements as-is, they're clear
            pass
        
        # Ensure reasonable length (but complete)
        if len(summary) > 120:
            # Find last complete word before 120 chars
            truncated = summary[:117]
            last_space = truncated.rfind(' ')
            if last_space > 80:  # Only truncate if we have a reasonable amount
                summary = summary[:last_space] + '...'
        
        return summary.strip()


if __name__ == "__main__":
    # Test ContentAgent
    async def test_content_agent():
        print("Testing ContentAgent...")
        
        # Create mock transcript segments for testing
        mock_segments = [
            TranscriptSegment(0.0, 10.0, "Welcome to our project presentation on sales automation.", 0.9),
            TranscriptSegment(10.0, 25.0, "Our goal is to increase sales efficiency by 40% through AI integration.", 0.9),
            TranscriptSegment(25.0, 45.0, "The data shows significant improvement in lead conversion rates.", 0.8),
            TranscriptSegment(45.0, 60.0, "Our recommendation is to implement this solution company-wide.", 0.9),
            TranscriptSegment(60.0, 75.0, "Next steps include pilot testing and stakeholder approval.", 0.8),
        ]
        
        agent = ContentAgent("test_content_job")
        result = await agent.batch_summarize(mock_segments, max_bullets=5)
        
        print(f"Content summarization: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Model used: {result.model_used}")
        print(f"Cache hit: {result.cache_hit}")
        print(f"Tokens used: {result.tokens_used}")
        
        if result.summary:
            print(f"\nBullet Points ({len(result.summary.bullet_points)}):")
            for i, bullet in enumerate(result.summary.bullet_points):
                print(f"  {i+1}. [{bullet.timestamp}] {bullet.text} (conf: {bullet.confidence:.2f})")
            
            print(f"\nMain Themes: {', '.join(result.summary.main_themes)}")
            print(f"Duration: {result.summary.total_duration}")
            print(f"Overall Confidence: {result.summary.summary_confidence:.2f}")
        
        if result.error:
            print(f"Error: {result.error}")
    
    asyncio.run(test_content_agent())
