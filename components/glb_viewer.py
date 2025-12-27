# components/glb_viewer.py
import streamlit as st
import streamlit.components.v1 as components
import base64
import os

def render_glb_viewer(glb_path: str, height: int = 600, width: str = "100%"):
    """
    Render a 3D GLB file viewer using Three.js
    
    Args:
        glb_path: Path to the .glb file
        height: Height of the viewer in pixels
        width: Width of the viewer (default 100%)
    """
    if not os.path.exists(glb_path):
        st.error(f"GLB file not found: {glb_path}")
        return
    
    # Read and encode the GLB file
    with open(glb_path, "rb") as f:
        glb_data = f.read()
    
    glb_base64 = base64.b64encode(glb_data).decode()
    
    # Three.js viewer HTML
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; overflow: hidden; }}
            #viewer {{ width: 100%; height: {height}px; }}
            #loading {{ 
                position: absolute; 
                top: 50%; 
                left: 50%; 
                transform: translate(-50%, -50%);
                font-family: Arial, sans-serif;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div id="loading">Loading 3D Model...</div>
        <div id="viewer"></div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        
        <script>
            // Scene setup
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf0f0f0);
            
            // Camera
            const camera = new THREE.PerspectiveCamera(
                75, 
                window.innerWidth / {height}, 
                0.1, 
                1000
            );
            camera.position.set(20, 20, 20);
            
            // Renderer
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, {height});
            document.getElementById('viewer').appendChild(renderer.domElement);
            
            // Controls
            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            
            // Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(10, 10, 10);
            scene.add(directionalLight);
            
            // Grid helper
            const gridHelper = new THREE.GridHelper(50, 50);
            scene.add(gridHelper);
            
            // Axes helper
            const axesHelper = new THREE.AxesHelper(10);
            scene.add(axesHelper);
            
            // Load GLB from base64
            const loader = new THREE.GLTFLoader();
            const glbData = atob('{glb_base64}');
            const glbArray = new Uint8Array(glbData.length);
            for (let i = 0; i < glbData.length; i++) {{
                glbArray[i] = glbData.charCodeAt(i);
            }}
            const glbBlob = new Blob([glbArray], {{ type: 'model/gltf-binary' }});
            const glbUrl = URL.createObjectURL(glbBlob);
            
            loader.load(
                glbUrl,
                function(gltf) {{
                    document.getElementById('loading').style.display = 'none';
                    
                    // Add model to scene
                    scene.add(gltf.scene);
                    
                    // Center and scale model
                    const box = new THREE.Box3().setFromObject(gltf.scene);
                    const center = box.getCenter(new THREE.Vector3());
                    const size = box.getSize(new THREE.Vector3());
                    
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const scale = 20 / maxDim;
                    gltf.scene.scale.multiplyScalar(scale);
                    
                    gltf.scene.position.x = -center.x * scale;
                    gltf.scene.position.y = -center.y * scale;
                    gltf.scene.position.z = -center.z * scale;
                    
                    // Adjust camera
                    camera.position.set(size.x * 2, size.y * 2, size.z * 2);
                    controls.update();
                }},
                function(xhr) {{
                    console.log((xhr.loaded / xhr.total * 100) + '% loaded');
                }},
                function(error) {{
                    console.error('Error loading GLB:', error);
                    document.getElementById('loading').innerHTML = 'Error loading model';
                }}
            );
            
            // Animation loop
            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
            
            // Handle window resize
            window.addEventListener('resize', function() {{
                camera.aspect = window.innerWidth / {height};
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, {height});
            }});
        </script>
    </body>
    </html>
    """
    
    # Render the viewer
    components.html(html_code, height=height)


def show_geometry_gallery(geometry_dir: str = "data/outputs/geometry"):
    """
    Display a gallery of all available GLB files with viewer
    """
    if not os.path.exists(geometry_dir):
        os.makedirs(geometry_dir, exist_ok=True)
        st.info(f"Geometry directory created: {geometry_dir}")
        return
    
    glb_files = [f for f in os.listdir(geometry_dir) if f.endswith('.glb')]
    
    if not glb_files:
        st.info("No geometry files found yet. Generate some specs to create 3D models!")
        return
    
    st.markdown(f"### 🏗️ 3D Geometry Gallery ({len(glb_files)} models)")
    
    # Dropdown to select model
    selected_file = st.selectbox(
        "Select a 3D model to view:",
        options=glb_files,
        format_func=lambda x: x.replace('.glb', '')
    )
    
    if selected_file:
        glb_path = os.path.join(geometry_dir, selected_file)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**Viewing:** `{selected_file}`")
            render_glb_viewer(glb_path, height=500)
        
        with col2:
            st.markdown("**Controls:**")
            st.markdown("🖱️ **Left Click + Drag**: Rotate")
            st.markdown("🖱️ **Right Click + Drag**: Pan")
            st.markdown("🖱️ **Scroll**: Zoom")
            st.markdown("---")
            
            # File info
            file_size = os.path.getsize(glb_path) / 1024  # KB
            st.markdown(f"**File Size:** {file_size:.2f} KB")
            
            # Download button
            with open(glb_path, "rb") as f:
                st.download_button(
                    label="📥 Download GLB",
                    data=f,
                    file_name=selected_file,
                    mime="model/gltf-binary"
                )


