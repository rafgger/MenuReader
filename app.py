"""
Menu Image Analyzer - Hugging Face Spaces Gradio Interface

This module provides a Gradio interface for the Menu Image Analyzer application,
optimized for deployment on Hugging Face Spaces.
"""

import gradio as gr
import os
import logging
import tempfile
import inspect
import base64
import io
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
import json
from html import escape

# Import the core application components
from app.services.ai_menu_processor import AIMenuProcessor
from app.services.secure_api_client import SecureAPIClient
from app.models.data_models import RequestCache, EnrichedDish, ProcessingError
from app.config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize global components with AI-based processor
api_client = SecureAPIClient()
shared_cache = RequestCache()
menu_processor = AIMenuProcessor(api_client=api_client, cache=shared_cache)

def process_menu_image(image: Image.Image) -> Tuple[str, str]:
    """
    Process uploaded menu image and return formatted results.
    
    Args:
        image: PIL Image object from Gradio
        
    Returns:
        Tuple of (HTML results, JSON results)
    """
    try:
        if image is None:
            return "<p>Please upload an image or take a camera snapshot before pressing Analyze Menu.</p>", "{}"
        
        # Convert PIL image to bytes using BytesIO (Windows-safe)
        import io
        img_buffer = io.BytesIO()
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.save(img_buffer, format='JPEG', quality=95)
        image_data = img_buffer.getvalue()
        img_buffer.close()
        
        # Generate processing ID
        import uuid
        processing_id = str(uuid.uuid4())[:16]
        
        logger.info(f"Processing menu image: {processing_id}, size: {len(image_data)} bytes")
        
        # Process the menu
        result = menu_processor.process_menu(
            image_data=image_data,
            processing_id=processing_id
        )
        
        if not result.success:
            error_messages = [error.message for error in result.errors]
            logger.error("Menu processing failed (%s): %s", processing_id, "; ".join(error_messages))
            return (
                f"<p><strong>Processing failed:</strong> {escape('; '.join(error_messages))}</p>",
                format_results_json(result.dishes, result.errors, result.processing_time),
            )
        
        # Format results for display
        html_output = format_results_html(result.dishes, result.errors)
        json_output = format_results_json(result.dishes, result.errors, result.processing_time)
        
        logger.info(f"Processing completed: {processing_id}, found {len(result.dishes)} dishes")
        
        return html_output, json_output
        
    except Exception as e:
        logger.error(f"Error processing menu image: {e}", exc_info=True)
        return f"❌ **Error**: {str(e)}", "{}"


def analyze_menu_with_status(image, camera_frame=""):
    """Keep analysis feedback next to the camera on narrow phone screens."""
    if camera_frame:
        try:
            if not camera_frame.startswith("data:image/jpeg;base64,"):
                raise ValueError(camera_frame)
            image = Image.open(io.BytesIO(base64.b64decode(camera_frame.split(",", 1)[1])))
            image.load()
        except Exception:
            message = "Could not capture the camera. Wait for the live preview and try Analyze Menu again, or upload a photo."
            yield message, f"<p>{message}</p>", "{}", gr.skip()
            return
    if image is None:
        message = "Open the camera and wait for the live preview, or upload a photo. Then press Analyze Menu."
        yield message, f"<p>{message}</p>", "{}", gr.skip()
        return

    # Publish the exact captured frame before starting the slow analysis call.
    yield "Analyzing this photo. Please wait...", "<p>Analyzing your menu...</p>", "{}", image
    html_output, json_output = process_menu_image(image)
    result = json.loads(json_output)
    if result.get("success"):
        status = f"Analysis complete: found {result['dishes_found']} dishes. Scroll down to Analysis Results."
    else:
        status = "Analysis could not complete. See Analysis Results below for details."
    yield status, html_output, json_output, gr.skip()


def format_results_html(dishes: List[EnrichedDish], errors: List[ProcessingError]) -> str:
    """
    Format processing results as HTML for display.
    
    Args:
        dishes: List of enriched dish objects
        errors: List of processing errors
        
    Returns:
        Formatted HTML string
    """
    if not dishes:
        return "<p style='color: red;'>❌ <strong>No dishes found</strong>. Please try uploading a clearer image of the menu.</p>"
    
    html_parts = [f"<p style='color: green;'>✅ <strong>Found {len(dishes)} dishes:</strong></p>"]
    
    for i, enriched_dish in enumerate(dishes, 1):
        dish = enriched_dish.dish
        description = enriched_dish.description
        images = enriched_dish.images
        
        # Start dish container
        html_parts.append(f"<div style='border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;'>")
        
        # Dish header
        html_parts.append(f"<h3>{i}. {dish.name}</h3>")
        
        # Price
        if dish.price:
            html_parts.append(f"<p><strong>Price:</strong> {dish.price}</p>")
        
        # Primary image
        if images and images.get('primary'):
            primary_image = images['primary']
            if isinstance(primary_image, dict) and primary_image.get('url'):
                html_parts.append(f"<p><strong>Main Image:</strong></p>")
                html_parts.append(f"<img src='{primary_image['url']}' alt='{dish.name}' style='max-width: 300px; height: auto; border-radius: 5px; margin: 10px 0;'>")
        
        # Secondary/Alternative images
        if images and images.get('secondary') and len(images['secondary']) > 0:
            html_parts.append(f"<p><strong>Alternative Images:</strong></p>")
            html_parts.append("<div style='display: flex; flex-wrap: wrap; gap: 10px;'>")
            for idx, secondary_image in enumerate(images['secondary'][:3], 1):  # Show up to 3 alternatives
                if isinstance(secondary_image, dict) and secondary_image.get('url'):
                    html_parts.append(f"<img src='{secondary_image['url']}' alt='{dish.name} - Alternative {idx}' style='max-width: 150px; height: auto; border-radius: 5px;'>")
            html_parts.append("</div>")
            
            if len(images['secondary']) > 3:
                html_parts.append(f"<p><em>({len(images['secondary']) - 3} more images available)</em></p>")
        
        # Description
        if description and description.text:
            html_parts.append(f"<p><strong>Description:</strong> {description.text}</p>")
            
            # Additional details
            if description.ingredients:
                ingredients_str = ", ".join(description.ingredients[:5])  # Limit to first 5
                if len(description.ingredients) > 5:
                    ingredients_str += f" (and {len(description.ingredients) - 5} more)"
                html_parts.append(f"<p><strong>Key Ingredients:</strong> {ingredients_str}</p>")
            
            if description.dietary_restrictions:
                dietary_str = ", ".join(description.dietary_restrictions)
                html_parts.append(f"<p><strong>Dietary Info:</strong> {dietary_str}</p>")
            
            if description.cuisine_type:
                html_parts.append(f"<p><strong>Cuisine:</strong> {description.cuisine_type}</p>")
            
            if description.spice_level:
                html_parts.append(f"<p><strong>Spice Level:</strong> {description.spice_level}</p>")
        
        # Confidence score
        if dish.confidence < 0.8:
            html_parts.append(f"<p><em>Note: Low confidence extraction ({dish.confidence:.1%})</em></p>")
        
        # Close dish container
        html_parts.append("</div>")
    
    # Add errors if any
    if errors:
        html_parts.append("<h3 style='color: orange;'>⚠️ Processing Notes:</h3>")
        html_parts.append("<ul>")
        for error in errors:
            if error.recoverable:
                html_parts.append(f"<li>{error.message}</li>")
        html_parts.append("</ul>")
    
    return "\n".join(html_parts)


def format_results_json(dishes: List[EnrichedDish], errors: List[ProcessingError], processing_time: float) -> str:
    """
    Format processing results as JSON string.
    
    Args:
        dishes: List of enriched dish objects
        errors: List of processing errors
        processing_time: Time taken for processing
        
    Returns:
        JSON string representation of results
    """
    try:
        results = {
            "success": len(dishes) > 0,
            "dishes_found": len(dishes),
            "processing_time_seconds": round(processing_time, 2),
            "dishes": [],
            "errors": []
        }
        
        # Format dishes
        for enriched_dish in dishes:
            dish = enriched_dish.dish
            description = enriched_dish.description
            images = enriched_dish.images
            
            dish_data = {
                "name": dish.name,
                "price": dish.price,
                "confidence": round(dish.confidence, 3),
                "description": None,
                "images": {
                    "primary": None,
                    "secondary_count": 0
                }
            }
            
            # Add description
            if description:
                dish_data["description"] = {
                    "text": description.text,
                    "ingredients": description.ingredients,
                    "dietary_restrictions": description.dietary_restrictions,
                    "cuisine_type": description.cuisine_type,
                    "spice_level": description.spice_level,
                    "preparation_method": description.preparation_method
                }
            
            # Add image info
            if images:
                if images.get('primary'):
                    primary = images['primary']
                    if isinstance(primary, dict):
                        dish_data["images"]["primary"] = primary.get('url')
                
                if images.get('secondary'):
                    dish_data["images"]["secondary_count"] = len(images['secondary'])
            
            results["dishes"].append(dish_data)
        
        # Format errors
        for error in errors:
            results["errors"].append({
                "type": error.type.value if hasattr(error.type, 'value') else str(error.type),
                "message": error.message,
                "recoverable": error.recoverable
            })
        
        return json.dumps(results, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error formatting JSON results: {e}")
        return json.dumps({"error": f"Failed to format results: {str(e)}"}, indent=2)


def get_api_status() -> str:
    """
    Get the status of API configurations.
    
    Returns:
        HTML formatted status information
    """
    try:
        config = get_config()
        
        # Check API key configurations for AI-based services
        ai_analyzer_configured = bool(os.getenv('OPENROUTER_API_KEY') or os.getenv('GOOGLE_API_KEY'))
        google_search_configured = bool(os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_ENGINE_ID'))
        openai_configured = bool(os.getenv('OPENAI_API_KEY'))
        
        status_parts = ["### 🔧 API Configuration Status\n"]
        
        # AI Menu Analyzer Service
        status_icon = "✅" if ai_analyzer_configured else "❌"
        ai_model = os.getenv('AI_MODEL', 'openai/gpt-4o')
        status_parts.append(f"{status_icon} **AI Menu Analyzer**: {'Configured' if ai_analyzer_configured else 'Not configured'}")
        if ai_analyzer_configured:
            status_parts.append(f"   Model: {ai_model}")
        
        # Google Image Search
        status_icon = "✅" if google_search_configured else "❌"
        status_parts.append(f"{status_icon} **Image Search**: {'Configured' if google_search_configured else 'Not configured'}")
        
        # OpenAI Descriptions
        status_icon = "✅" if openai_configured else "❌"
        status_parts.append(f"{status_icon} **AI Descriptions**: {'Configured' if openai_configured else 'Not configured'}")
        
        # Overall status
        all_configured = ai_analyzer_configured and google_search_configured and openai_configured
        if all_configured:
            status_parts.append("\n✅ **All services configured** - Full functionality available")
        else:
            status_parts.append("\n⚠️ **Some services not configured** - Limited functionality")
            status_parts.append("\nPlease configure missing API keys in the Hugging Face Spaces settings.")
        
        return "\n".join(status_parts)
        
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return f"❌ **Error checking API status**: {str(e)}"


# Create Gradio interface
def create_gradio_interface():
    """Create and configure the Gradio interface."""
    
    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto !important;
    }
    .output-markdown {
        max-height: 600px;
        overflow-y: auto;
    }
    .json-output {
        max-height: 400px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 12px;
    }
    """
    
    with gr.Blocks(
        title="Menu Image Analyzer",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as interface:
        
        # Header
        gr.Markdown("""
        # 🍽️ AI Menu Analyzer
        
        Transform menu photos into rich, visual dining guides using AI vision models! Upload a photo of a restaurant menu 
        and get detailed information about each dish including images and AI-generated descriptions.
        
        **Powered by:** AI Vision Models (GPT-4o, Gemini Pro Vision)  
        **Supported formats:** JPEG, PNG, WebP  
        **Languages:** Multi-language menu support
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                # Input section
                gr.Markdown("### 📤 Upload Menu Image")
                # Gradio 6 moved mirror_webcam into WebcamOptions.
                camera_options = (
                    {"webcam_options": gr.WebcamOptions(
                        mirror=False,
                        constraints={"video": {"facingMode": {"ideal": "environment"}}},
                    )}
                    if "webcam_options" in inspect.signature(gr.Image).parameters
                    else {"mirror_webcam": False}
                )
                image_input = gr.Image(
                    label="Menu Photo",
                    type="pil",
                    height=400,
                    elem_id="menu-camera",
                    # Start in camera mode so the camera capture control is immediately visible.
                    sources=["webcam", "upload"],
                    **camera_options
                )
                
                process_btn = gr.Button(
                    "🔍 Analyze Menu",
                    variant="primary",
                    size="lg"
                )
                analysis_status = gr.Markdown(
                    "Point the camera at your menu and press Analyze Menu to take and analyze a photo. "
                    "You can also upload a photo."
                )
                camera_frame = gr.Textbox(visible=False)
                
                # API Status
                gr.Markdown("### 📊 System Status")
                status_output = gr.Markdown(
                    value=get_api_status(),
                    label="API Status"
                )
                
                # Refresh status button
                refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                refresh_btn.click(
                    fn=get_api_status,
                    outputs=status_output
                )
            
            with gr.Column(scale=2):
                # Output section
                gr.Markdown("### 📋 Analysis Results")
                
                with gr.Tabs():
                    with gr.TabItem("📖 Formatted Results"):
                        results_output = gr.HTML(
                            label="Dish Information",
                            value="<p>Upload a menu image to see detailed dish information here.</p>",
                            elem_classes=["output-html"]
                        )
                    
                    with gr.TabItem("🔧 JSON Data"):
                        json_output = gr.Code(
                            label="Raw JSON Results",
                            language="json",
                            value="{}",
                            elem_classes=["json-output"]
                        )
        
        # Processing event
        process_btn.click(
            fn=analyze_menu_with_status,
            inputs=[image_input, camera_frame],
            outputs=[analysis_status, results_output, json_output, image_input],
            js=Path(__file__).with_name("camera_capture.js").read_text(encoding="utf-8"),
            show_progress="full",
            show_progress_on=[analysis_status, results_output]
        )
        
        # Footer
        gr.Markdown("""
        ---
        ### 💡 Tips for Best Results
        - Use clear, well-lit photos of menus
        - Ensure text is readable and not blurry
        - Try to capture the entire menu section you're interested in
        - Works with menus in multiple languages
    
        [Report an issue](https://github.com/rafgger/MenuReader/issues/)
        """)
    
    return interface


# Create the interface
demo = create_gradio_interface()

# Launch configuration for Hugging Face Spaces
if __name__ == "__main__":
    # An explicit phone-testing request takes precedence over SPACE_ID from .env.
    share_enabled = os.getenv("GRADIO_SHARE", "false").strip().lower() == "true"
    is_spaces = bool(os.getenv("SPACE_ID", "").strip())
    
    if is_spaces and not share_enabled:
        logger.info("Running on Hugging Face Spaces")
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False
        )
    else:
        logger.info("Running locally")
        # Use environment variable to control debug mode (default: False for production)
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        demo.launch(
            share=share_enabled,
            show_error=True,
            debug=debug_mode
        )
