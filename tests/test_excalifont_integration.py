"""Tests for Excalifont integration, discovery, rendering, persistence, and MCP tools."""

import asyncio
import io
import os
from pathlib import Path
from unittest.mock import patch
from PIL import Image

import pytest
from fastmcp import Client

from excalidraw_mcp.elements import normalize_font_family, text, rect
from excalidraw_mcp.fonts import FontRegistry, get_font, list_fonts, registry
from excalidraw_mcp.renderer import render_scene_image, render_scene_to_png
from excalidraw_mcp.service import SceneService, _label_for
from excalidraw_mcp.server import create_server


class TestFontRegistryAndExcalifontDiscovery:
    def test_bundled_excalifont_exists(self):
        assets_dir = Path(__file__).resolve().parent.parent / "excalidraw_mcp" / "assets" / "fonts"
        font_file = assets_dir / "Excalifont-Regular.ttf"
        license_file = assets_dir / "OFL.txt"
        assert font_file.is_file(), f"Font file missing at {font_file}"
        assert license_file.is_file(), f"License file missing at {license_file}"
        assert font_file.stat().st_size > 50_000

    def test_registry_discovers_excalifont(self):
        reg = FontRegistry()
        reg.discover(force=True)
        assert "excalifont" in reg._by_family
        records = reg._by_family["excalifont"]
        assert len(records) >= 1
        assert records[0]["family"] == "Excalifont"
        assert records[0]["category"] == "handwriting"
        assert records[0]["style"] == "Regular"

    def test_get_font_by_int_and_family_name(self):
        # By integer 1 (Excalidraw schema code for Excalifont/Virgil)
        font_by_int = get_font(1, 24)
        assert font_by_int.getname() == ("Excalifont", "Regular")

        # By family name (case-insensitive)
        font_by_name = get_font("excalifont", 24)
        assert font_by_name.getname() == ("Excalifont", "Regular")

        font_by_upper = get_font("Excalifont", 24)
        assert font_by_upper.getname() == ("Excalifont", "Regular")

        # By alias 'virgil'
        font_by_alias = get_font("virgil", 24)
        assert font_by_alias.getname() == ("Excalifont", "Regular")

        # By category 'handwriting'
        font_by_cat = get_font("handwriting", 24)
        assert font_by_cat.getname() == ("Excalifont", "Regular")

    def test_fallback_when_invalid_font_requested(self):
        # Non-existent font should gracefully fall back to a valid ImageFont without crashing
        font = get_font("completely_nonexistent_font_12345", 18)
        assert font is not None
        bbox = font.getbbox("Hello")
        assert bbox[2] > bbox[0]

    def test_fallback_when_bundled_font_missing(self, tmp_path):
        # Empty registry with no fonts found should fall back to Pillow default
        empty_reg = FontRegistry()
        with patch.object(empty_reg, "_scan_directory"):
            with patch("shutil.which", return_value=None):
                with patch("excalidraw_mcp.fonts._get_font_directories", return_value=[]):
                    empty_reg.discover(force=True)
                    font = empty_reg.load_font(family="excalifont", size=20)
                    assert font is not None
                    bbox = font.getbbox("Fallback Test")
                    assert bbox is not None


class TestFontNormalizationAndElements:
    def test_normalize_font_family_mappings(self):
        assert normalize_font_family(None) == 2
        assert normalize_font_family(1) == 1
        assert normalize_font_family(2) == 2
        assert normalize_font_family(3) == 3
        assert normalize_font_family(4) == 4
        assert normalize_font_family("1") == 1
        assert normalize_font_family("excalifont") == 1
        assert normalize_font_family("Excalifont") == 1
        assert normalize_font_family("virgil") == 1
        assert normalize_font_family("handwriting") == 1
        assert normalize_font_family("hand") == 1
        assert normalize_font_family("sans-serif") == 2
        assert normalize_font_family("helvetica") == 2
        assert normalize_font_family("monospace") == 3
        assert normalize_font_family("code") == 3
        assert normalize_font_family("cascadia") == 3
        assert normalize_font_family("comic-shanns") == 4
        assert normalize_font_family("unknown-random-font") == 2

    def test_text_element_creation_with_font_family(self):
        el_default = text(0, 0, "Default text")
        assert el_default["fontFamily"] == 2

        el_excalifont = text(0, 0, "Handwritten note", fontFamily="excalifont")
        assert el_excalifont["fontFamily"] == 1

        el_int = text(0, 0, "Integer font", fontFamily=1)
        assert el_int["fontFamily"] == 1

        el_kwarg = text(0, 0, "Kwarg font", font_family="excalifont")
        assert el_kwarg["fontFamily"] == 1


class TestSceneServiceExcalifontOperations:
    def test_add_text_with_excalifont(self):
        service = SceneService()
        res = service.add_text(100, 200, "Architectural Draft", font_size=24, font_family="excalifont")
        txt_id = res["text_id"]
        el_info = service.get_element(txt_id)
        el = el_info["element"]
        assert el["fontFamily"] == 1
        assert el["fontSize"] == 24
        assert el["text"] == "Architectural Draft"

    def test_update_element_font_family(self):
        service = SceneService()
        res = service.add_text(50, 50, "Update me", font_size=16)
        txt_id = res["text_id"]
        assert service.get_element(txt_id)["element"]["fontFamily"] == 2

        service.update_element(txt_id, font_family="excalifont", font_size=28)
        updated = service.get_element(txt_id)["element"]
        assert updated["fontFamily"] == 1
        assert updated["fontSize"] == 28

    def test_shape_label_with_excalifont(self):
        service = SceneService()
        res = service.add_shape("rectangle", 10, 10, 120, 80, label="Box Title", font_family="excalifont")
        rect_id = res["rectangle_id"]
        lbl_id = res["label_id"]
        assert lbl_id is not None
        lbl = service.get_element(lbl_id)["element"]
        assert lbl["fontFamily"] == 1

    def test_update_shape_label_font(self):
        service = SceneService()
        res = service.add_shape("rectangle", 0, 0, 100, 50, label="Initial")
        rect_id = res["rectangle_id"]
        lbl_id = res["label_id"]
        assert service.get_element(lbl_id)["element"]["fontFamily"] == 2

        service.update_element(rect_id, font_family="excalifont")
        lbl = service.get_element(lbl_id)["element"]
        assert lbl["fontFamily"] == 1

    def test_batch_mutate_with_excalifont(self):
        service = SceneService()
        ops = [
            {
                "action": "add_text",
                "client_id": "txt1",
                "x": 100,
                "y": 100,
                "content": "Batch Note",
                "font_family": "excalifont",
                "font_size": 22,
            },
            {
                "action": "add_rectangle",
                "client_id": "box1",
                "x": 200,
                "y": 200,
                "w": 150,
                "h": 100,
                "label": "Box",
            },
            {
                "action": "update_element",
                "element_id": "box1",
                "font_family": "excalifont",
            },
        ]
        res = service.batch_mutate(ops)
        assert res["operations_executed"] == 3
        txt_id = res["ref_map"]["txt1"]
        box_id = res["ref_map"]["box1"]
        assert service.get_element(txt_id)["element"]["fontFamily"] == 1
        lbl = _label_for(_active_dict(service), box_id)
        assert lbl["fontFamily"] == 1

    def test_list_fonts_includes_excalifont(self):
        service = SceneService()
        fonts_res = service.list_fonts()
        assert fonts_res["defaults"].get("handwriting") == "Excalifont"
        names = [f["family"] for f in fonts_res["fonts"]]
        assert "Excalifont" in names


class TestRenderingAndExportCompatibility:
    def test_render_png_with_excalifont(self):
        service = SceneService()
        service.add_text(50, 50, "Excalifont Heading", font_size=32, font_family="excalifont")
        service.add_shape("rectangle", 50, 120, 200, 100, label="Annotated Node", font_family="excalifont")
        service.add_text(50, 250, "Standard Sans-serif Text", font_size=20, font_family="sans-serif")
        service.add_text(50, 300, "def foo(): pass", font_size=18, font_family="monospace")

        doc, _ = service.state.snapshot()
        png_bytes, width, height = render_scene_image(doc, scale=1.0)
        assert len(png_bytes) > 0
        assert width > 0 and height > 0

        # Verify PIL can open the generated PNG image
        img = Image.open(io.BytesIO(png_bytes))
        assert img.format == "PNG"
        assert img.size == (width, height)

    def test_export_scene_and_url_preserves_font_family(self, tmp_path):
        with patch.dict(os.environ, {"EXCALIDRAW_SCENE_DIR": str(tmp_path)}):
            service = SceneService()
            service.add_text(100, 100, "Web URL Note", font_size=20, font_family="excalifont")
            
            # Test export_to_excalidraw_url
            url_res = service.export_to_excalidraw_url()
            assert "url" in url_res
            assert url_res["url"].startswith("https://excalidraw.com/#json=")

            # Test save and load
            service.save("excalifont_scene")

            # Load into fresh service
            new_service = SceneService()
            new_service.load("excalifont_scene")
            doc, _ = new_service.state.snapshot()
            text_elements = [el for el in doc["elements"] if el["type"] == "text"]
            assert len(text_elements) == 1
            assert text_elements[0]["fontFamily"] == 1
            assert text_elements[0]["text"] == "Web URL Note"


class TestMcpServerExcalifontToolCalls:
    def test_mcp_server_add_text_tool_excalifont(self):
        server = create_server()
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        assert "add_text" in tools
        schema = tools["add_text"].parameters
        assert "font_family" in schema.get("properties", {})

    def test_mcp_server_update_element_tool_font_properties(self):
        server = create_server()
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        assert "update_element" in tools
        schema = tools["update_element"].parameters
        assert "font_family" in schema.get("properties", {})
        assert "font_size" in schema.get("properties", {})

    @pytest.mark.anyio
    async def test_mcp_client_tool_call_creates_excalifont_text(self):
        server = create_server()
        async with Client(server, timeout=5) as client:
            res = await client.call_tool(
                "add_text",
                {
                    "x": 100,
                    "y": 150,
                    "content": "MCP Agent handwritten text",
                    "font_size": 24,
                    "font_family": "excalifont",
                },
            )
            assert not res.is_error
            txt_id = res.structured_content["text_id"]

            elem_res = await client.call_tool("get_element", {"element_id": txt_id})
            assert not elem_res.is_error
            element = elem_res.structured_content["element"]
            assert element["fontFamily"] == 1
            assert element["fontSize"] == 24
            assert element["text"] == "MCP Agent handwritten text"


def _active_dict(service):
    doc, _ = service.state.snapshot()
    return {el["id"]: el for el in doc["elements"] if not el.get("isDeleted")}
