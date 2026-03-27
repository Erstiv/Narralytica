"""Narralytica: Export endpoints for SRT, JSON, CSV, DOCX."""
import csv
import io
from datetime import timedelta

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Episode, Scene, SceneObject

router = APIRouter(prefix="/export", tags=["export"])


def _fmt_ts(seconds: float) -> str:
    """Format seconds as SRT timecode: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_tc(seconds: float) -> str:
    """Format seconds as readable timecode: HH:MM:SS"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


async def _get_episode_scenes(episode_id: int, db: AsyncSession):
    """Load episode with all scenes and objects."""
    ep = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = ep.scalar_one_or_none()
    if not episode:
        raise HTTPException(404, "Episode not found")

    result = await db.execute(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .options(selectinload(Scene.objects))
        .order_by(Scene.start_timestamp)
    )
    scenes = result.scalars().all()
    if not scenes:
        raise HTTPException(404, "No scenes found for this episode")

    return episode, scenes


@router.get("/{episode_id}/srt")
async def export_srt(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Export diarized transcript as SRT subtitle file."""
    episode, scenes = await _get_episode_scenes(episode_id, db)

    lines = []
    counter = 1
    for scene in scenes:
        for entry in (scene.merged_transcript or []):
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            start = entry.get("start", scene.start_timestamp)
            end = entry.get("end", scene.end_timestamp)

            lines.append(str(counter))
            lines.append(f"{_fmt_ts(start)} --> {_fmt_ts(end)}")
            lines.append(f"[{speaker}] {text}")
            lines.append("")
            counter += 1

    if not lines:
        raise HTTPException(404, "No transcript data available")

    content = "\n".join(lines)
    filename = f"{episode.title.replace(' ', '_')}_S{episode.season:02d}E{episode.episode_number:02d}.srt"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{episode_id}/script-json")
async def export_script_json(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Export rich diarized script with word-level timestamps as JSON."""
    episode, scenes = await _get_episode_scenes(episode_id, db)

    script = {
        "episode": {
            "title": episode.title,
            "season": episode.season,
            "episode_number": episode.episode_number,
            "duration_seconds": episode.duration_seconds,
        },
        "scenes": [],
    }

    for scene in scenes:
        script["scenes"].append({
            "scene_number": scene.id,
            "start_timestamp": scene.start_timestamp,
            "end_timestamp": scene.end_timestamp,
            "characters": scene.characters_present,
            "transcript": scene.merged_transcript or [],
        })

    import json
    content = json.dumps(script, indent=2)
    filename = f"{episode.title.replace(' ', '_')}_script.json"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{episode_id}/metadata-json")
async def export_metadata_json(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Export full scene metadata as JSON."""
    episode, scenes = await _get_episode_scenes(episode_id, db)

    import json
    data = {
        "episode": {
            "title": episode.title,
            "season": episode.season,
            "episode_number": episode.episode_number,
        },
        "scenes": [],
    }

    for scene in scenes:
        data["scenes"].append({
            "id": scene.id,
            "start_timestamp": scene.start_timestamp,
            "end_timestamp": scene.end_timestamp,
            "duration": scene.duration,
            "characters_present": scene.characters_present,
            "key_dialog": scene.key_dialog,
            "actions": scene.actions,
            "interactions": scene.interactions,
            "mood_ambience": scene.mood_ambience,
            "color_palette": scene.color_palette,
            "tropes_memes": scene.tropes_memes,
            "background": scene.background,
            "overall_confidence": scene.overall_confidence,
            "description_text": scene.description_text,
            "objects": [
                {"name": o.name, "category": o.category, "prominence": o.prominence, "confidence": o.confidence}
                for o in scene.objects
            ],
        })

    content = json.dumps(data, indent=2)
    filename = f"{episode.title.replace(' ', '_')}_metadata.json"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{episode_id}/metadata-csv")
async def export_metadata_csv(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Export scene metadata as CSV (Excel-friendly)."""
    episode, scenes = await _get_episode_scenes(episode_id, db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Scene ID", "Start", "End", "Duration (s)", "Characters",
        "Actions", "Mood", "Background", "Objects", "Confidence",
        "Description",
    ])

    for scene in scenes:
        chars = ", ".join(
            c["name"] for c in (scene.characters_present or []) if isinstance(c, dict)
        )
        objects = ", ".join(o.name for o in scene.objects)

        writer.writerow([
            scene.id,
            _fmt_tc(scene.start_timestamp),
            _fmt_tc(scene.end_timestamp),
            round(scene.duration, 1),
            chars,
            scene.actions or "",
            scene.mood_ambience or "",
            scene.background or "",
            objects,
            scene.overall_confidence,
            scene.description_text or "",
        ])

    content = output.getvalue()
    filename = f"{episode.title.replace(' ', '_')}_metadata.csv"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),  # BOM for Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{episode_id}/script-docx")
async def export_script_docx(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Export formatted post-production script as DOCX."""
    episode, scenes = await _get_episode_scenes(episode_id, db)

    doc = DocxDocument()

    # Title
    title = doc.add_heading(level=0)
    run = title.add_run(f"{episode.title}")
    run.font.size = Pt(24)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(
        f"Season {episode.season}, Episode {episode.episode_number}\n"
        f"Generated by Narralytica"
    )
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(128, 128, 128)

    doc.add_paragraph()  # Spacer

    for scene in scenes:
        # Scene header
        header = doc.add_heading(level=1)
        header.add_run(
            f"Scene {scene.id} "
            f"[{_fmt_tc(scene.start_timestamp)} - {_fmt_tc(scene.end_timestamp)}]"
        )

        # Characters
        chars = [c["name"] for c in (scene.characters_present or []) if isinstance(c, dict)]
        if chars:
            p = doc.add_paragraph()
            run = p.add_run("Characters: ")
            run.bold = True
            run.font.size = Pt(10)
            run = p.add_run(", ".join(chars))
            run.font.size = Pt(10)

        # Setting
        if scene.background:
            p = doc.add_paragraph()
            run = p.add_run("Setting: ")
            run.bold = True
            run.font.size = Pt(10)
            run = p.add_run(scene.background)
            run.font.size = Pt(10)

        # Action/Description
        if scene.actions:
            p = doc.add_paragraph()
            run = p.add_run(scene.actions)
            run.italic = True
            run.font.size = Pt(10)

        # Dialog from merged transcript
        for entry in (scene.merged_transcript or []):
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            ts = entry.get("start")
            tc_str = f" [{_fmt_tc(ts)}]" if ts else ""

            p = doc.add_paragraph()
            run = p.add_run(f"{speaker.upper()}{tc_str}")
            run.bold = True
            run.font.size = Pt(10)

            p2 = doc.add_paragraph()
            p2.paragraph_format.left_indent = Pt(36)
            run = p2.add_run(text)
            run.font.size = Pt(10)

        doc.add_paragraph()  # Scene separator

    # Save to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    filename = f"{episode.title.replace(' ', '_')}_script.docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
