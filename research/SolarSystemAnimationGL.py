"""
Solar System Animation using OpenGL
Heliocentric view with Sun at center, showing Earth and Moon orbits
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import sys
import math
from astropy.time import Time
from astropy.coordinates import get_sun, get_body, solar_system_ephemeris
import astropy.units as u


class SolarSystemView:
    """OpenGL-based solar system visualization"""
    
    def __init__(self, start_time, end_time, frames_per_day=12, width=1200, height=900):
        """Initialize the solar system view
        
        Parameters
        ----------
        start_time : Time
            Animation start time (UTC)
        end_time : Time
            Animation end time (UTC)
        frames_per_day : int, optional
            Number of frames to calculate per day (default: 12)
        width, height : int
            Window dimensions
        """
        self.width = width
        self.height = height
        self.running = False
        self.clock = None
        
        # Time parameters
        self.start_time = start_time
        self.end_time = end_time
        self.frames_per_day = frames_per_day
        
        # Animation parameters
        self.current_frame = 0
        self.playing = True
        self.animation_speed = 1
        self.trail_length = 10000  # Number of past positions to show (full year at hourly intervals)
        self.gap_frames = 50  # Number of frames to clear around Earth/Moon for visibility
        
        # Use built-in ephemeris for faster calculations
        solar_system_ephemeris.set('builtin')
        
        # View control
        self.rotation_x = 0   # Tilt (0 = looking straight down)
        self.rotation_z = 0   # Rotation
        self.zoom = 2.0       # Camera distance (closer view)
        
        # Size scale factors (exaggerated for visibility)
        self.sun_size = 0.023      # Relative size (5x magnification)
        self.earth_size = 0.00125  # Halved again - approaching realistic proportions
        self.moon_size = 0.001     # Halved again - approaching realistic proportions
        
        # Moon orbit scale (true scale = 1.0)
        self.moon_orbit_scale = 1.0
        
        # Calculate positions
        self._calculate_positions()
        
    def _calculate_positions(self):
        """Calculate heliocentric positions of Earth and Moon for all frames"""
        import warnings
        from astropy.utils.exceptions import AstropyWarning
        
        # Calculate number of days in the time range
        duration_days = (self.end_time.jd - self.start_time.jd)
        
        # Calculate total number of frames
        self.n_frames = int(duration_days * self.frames_per_day)
        
        if self.n_frames < 1:
            raise ValueError("Time range too short or frames_per_day too low - need at least 1 frame")
        
        print(f"\nSetting up animation from {self.start_time.iso} to {self.end_time.iso} UTC")
        print(f"Duration: {duration_days:.2f} days")
        print(f"Frames per day: {self.frames_per_day}")
        print(f"Total frames: {self.n_frames}")
        print(f"Calculating positions...")
        
        # Create time array for the entire range
        self.times = self.start_time + np.linspace(0, duration_days, self.n_frames) * u.day
        
        # Pre-calculate all positions
        self.earth_positions = []  # List of (x, y, z) tuples
        self.moon_positions = []   # List of (x, y, z) tuples (scaled)
        self.moon_positions_actual = []  # List of actual (x, y, z) tuples
        
        # Suppress expected coordinate transformation warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', AstropyWarning)
            
            for i, t in enumerate(self.times):
                # Show progress
                if i % max(1, self.n_frames // 100) == 0 or i == self.n_frames - 1:
                    percent = (i + 1) / self.n_frames * 100
                    print(f"\rProgress: {i + 1}/{self.n_frames} ({percent:.1f}%)", end='', flush=True)
                
                # Get Sun position (barycentric)
                sun = get_sun(t)
                
                # Get Earth position (barycentric)
                earth = get_body('earth', t)
                
                # Get Moon position (barycentric)
                moon = get_body('moon', t)
        
                # Convert to heliocentric by subtracting Sun's position
                # Earth position (heliocentric)
                earth_helio = earth.cartesian - sun.cartesian
                earth_x = earth_helio.x.to(u.AU).value
                earth_y = earth_helio.y.to(u.AU).value
                earth_z = earth_helio.z.to(u.AU).value
                
                # Moon position (heliocentric)
                moon_helio = moon.cartesian - sun.cartesian
                moon_x_actual = moon_helio.x.to(u.AU).value
                moon_y_actual = moon_helio.y.to(u.AU).value
                moon_z_actual = moon_helio.z.to(u.AU).value
                
                # Calculate Moon offset from Earth and scale it
                moon_offset_x = (moon_x_actual - earth_x) * self.moon_orbit_scale
                moon_offset_y = (moon_y_actual - earth_y) * self.moon_orbit_scale
                moon_offset_z = (moon_z_actual - earth_z) * self.moon_orbit_scale
                
                # Apply scaled offset to get display position
                moon_x = earth_x + moon_offset_x
                moon_y = earth_y + moon_offset_y
                moon_z = earth_z + moon_offset_z
                
                # Store positions
                self.earth_positions.append((earth_x, earth_y, earth_z))
                self.moon_positions.append((moon_x, moon_y, moon_z))
                self.moon_positions_actual.append((moon_x_actual, moon_y_actual, moon_z_actual))
        
        print()  # New line after progress
        print(f"Animation setup complete!")
        print(f"Time range: {self.times[0].iso} to {self.times[-1].iso} UTC")
        
    def get_current_positions(self):
        """Get Earth and Moon positions for current frame"""
        self.earth_x, self.earth_y, self.earth_z = self.earth_positions[self.current_frame]
        self.moon_x, self.moon_y, self.moon_z = self.moon_positions[self.current_frame]
        self.moon_x_actual, self.moon_y_actual, self.moon_z_actual = self.moon_positions_actual[self.current_frame]
        self.current_time = self.times[self.current_frame]
        
    def initialize(self):
        """Initialize pygame and OpenGL"""
        pygame.init()
        
        # Set up display with OpenGL
        self.display = pygame.display.set_mode(
            (self.width, self.height),
            DOUBLEBUF | OPENGL
        )
        
        pygame.display.set_caption("Solar System View - Heliocentric")
        
        # Initialize OpenGL
        self._init_opengl()
        
        # Create clock for frame rate control
        self.clock = pygame.time.Clock()
        self.running = True
        
        print("\nOpenGL Solar System initialized")
        print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        
    def _init_opengl(self):
        """Configure OpenGL rendering"""
        # Background color (black for space)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        
        # Enable smooth lines and points
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Disable all lighting (using vertex colors only)
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        glDisable(GL_LIGHT1)
        glDisable(GL_LIGHT2)
        glDisable(GL_LIGHT3)
        glDisable(GL_LIGHT4)
        glDisable(GL_LIGHT5)
        glDisable(GL_LIGHT6)
        glDisable(GL_LIGHT7)
        glDisable(GL_COLOR_MATERIAL)
        
        # Disable back-face culling (draw all triangles regardless of orientation)
        glDisable(GL_CULL_FACE)
        
        # Use smooth shading (with lighting off, uniform vertex colors = uniform surface)
        glShadeModel(GL_SMOOTH)
        
        # Set up perspective
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (self.width / self.height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        
    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    # Reset view
                    self.rotation_x = 0
                    self.rotation_z = 0
                    self.zoom = 2.0
                elif event.key == pygame.K_SPACE:
                    # Toggle play/pause
                    self.playing = not self.playing
                    print(f"Animation {'playing' if self.playing else 'paused'}")
                elif event.key == pygame.K_UP:
                    # Speed up
                    self.animation_speed = min(10, self.animation_speed + 1)
                    print(f"Speed: {self.animation_speed}x")
                elif event.key == pygame.K_DOWN:
                    # Slow down
                    self.animation_speed = max(1, self.animation_speed - 1)
                    print(f"Speed: {self.animation_speed}x")
                elif event.key == pygame.K_LEFT:
                    # Step backward
                    self.current_frame = (self.current_frame - 1) % self.n_frames
                    print(f"Frame {self.current_frame + 1}/{self.n_frames}")
                elif event.key == pygame.K_RIGHT:
                    # Step forward
                    self.current_frame = (self.current_frame + 1) % self.n_frames
                    print(f"Frame {self.current_frame + 1}/{self.n_frames}")
                elif event.key == pygame.K_1:
                    # Zoom preset 1: Wide view
                    self.zoom = 2.0
                    print("Zoom: Wide view (2.0 AU)")
                elif event.key == pygame.K_2:
                    # Zoom preset 2: Medium view
                    self.zoom = 1.0
                    print("Zoom: Medium view (1.0 AU)")
                elif event.key == pygame.K_3:
                    # Zoom preset 3: Close view
                    self.zoom = 0.4
                    print("Zoom: Close view (0.4 AU)")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    self.zoom = max(1.0, self.zoom - 0.2)
                elif event.button == 5:  # Mouse wheel down
                    self.zoom = min(10.0, self.zoom + 0.2)
        
        # Mouse dragging
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:  # Left button
            mouse_rel = pygame.mouse.get_rel()
            self.rotation_z += mouse_rel[0] * 0.5
            self.rotation_x += mouse_rel[1] * 0.5
            # Clamp tilt
            self.rotation_x = max(-90, min(90, self.rotation_x))
        else:
            pygame.mouse.get_rel()
            
    def update(self):
        """Update animation state"""
        if self.playing:
            self.current_frame = (self.current_frame + self.animation_speed) % self.n_frames
            
    def draw_sphere(self, radius, slices=32, stacks=32):
        """Draw a sphere using triangle strips - no lighting, pure color"""
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = radius * math.sin(lat0)
            zr0 = radius * math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
            z1 = radius * math.sin(lat1)
            zr1 = radius * math.cos(lat1)
            
            glBegin(GL_TRIANGLE_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                # Don't set normals, just vertices with current color
                glVertex3f(x * zr0, y * zr0, z0)
                glVertex3f(x * zr1, y * zr1, z1)
            glEnd()
        
    def draw_sun(self):
        """Draw the Sun at the origin"""
        glPushMatrix()
        
        # Draw Sun only (no glow for now to debug)
        glColor3f(1.0, 1.0, 0.0)
        self.draw_sphere(self.sun_size, slices=64, stacks=64)
        
        glPopMatrix()
        
    def draw_earth(self):
        """Draw Earth at its orbital position"""
        glPushMatrix()
        glTranslatef(self.earth_x, self.earth_y, self.earth_z)
        
        # Draw Earth
        glColor3f(0.2, 0.5, 1.0)  # Blue
        self.draw_sphere(self.earth_size)
        
        glPopMatrix()
        
    def draw_moon(self):
        """Draw Moon at its orbital position"""
        glPushMatrix()
        glTranslatef(self.moon_x, self.moon_y, self.moon_z)
        
        # Draw Moon
        glColor3f(0.8, 0.8, 0.8)  # Gray
        self.draw_sphere(self.moon_size)
        
        glPopMatrix()
        
    def draw_earth_trail(self):
        """Draw Earth's orbital trail"""
        if self.current_frame < 2:
            return  # Need at least 2 frames
            
        # Calculate trail range (stop before gap_frames to clear space around Earth)
        start_frame = max(0, self.current_frame - self.trail_length)
        end_frame = max(0, self.current_frame - self.gap_frames)
        
        if end_frame <= start_frame:
            return  # No trail to draw
        
        glLineWidth(1.5)
        glBegin(GL_LINE_STRIP)
        
        # Draw trail with fading transparency
        for i in range(start_frame, end_frame + 1):
            # Calculate alpha based on age (newer = more opaque)
            age = self.current_frame - i
            alpha = 1.0 - (age / self.trail_length)
            glColor4f(0.2, 0.5, 1.0, alpha * 0.6)  # Blue with fading
            
            x, y, z = self.earth_positions[i]
            glVertex3f(x, y, z)
        
        glEnd()
        
    def draw_moon_trail(self):
        """Draw Moon's orbital trail"""
        if self.current_frame < 2:
            return  # Need at least 2 frames
            
        # Calculate trail range (stop before gap_frames to clear space around Moon)
        start_frame = max(0, self.current_frame - self.trail_length)
        end_frame = max(0, self.current_frame - self.gap_frames)
        
        if end_frame <= start_frame:
            return  # No trail to draw
        
        glLineWidth(1.0)
        glBegin(GL_LINE_STRIP)
        
        # Draw trail with fading transparency
        for i in range(start_frame, end_frame + 1):
            # Calculate alpha based on age (newer = more opaque)
            age = self.current_frame - i
            alpha = 1.0 - (age / self.trail_length)
            glColor4f(0.8, 0.8, 0.8, alpha * 0.5)  # Gray with fading
            
            x, y, z = self.moon_positions[i]
            glVertex3f(x, y, z)
        
        glEnd()
        
    def draw_earth_orbit(self):
        """Draw the complete orbital path of Earth with gap around current position"""
        if len(self.earth_positions) < 2:
            return
        
        # Calculate gap boundaries
        gap_start = max(0, self.current_frame - self.gap_frames)
        gap_end = min(len(self.earth_positions) - 1, self.current_frame + self.gap_frames)
        
        glLineWidth(1.0)
        glColor4f(0.2, 0.5, 1.0, 0.3)  # Blue with transparency
        
        # Draw segment before gap
        if gap_start > 0:
            glBegin(GL_LINE_STRIP)
            for i in range(0, gap_start + 1):
                x, y, z = self.earth_positions[i]
                glVertex3f(x, y, z)
            glEnd()
        
        # Draw segment after gap
        if gap_end < len(self.earth_positions) - 1:
            glBegin(GL_LINE_STRIP)
            for i in range(gap_end, len(self.earth_positions)):
                x, y, z = self.earth_positions[i]
                glVertex3f(x, y, z)
            glEnd()
        
    def draw_moon_orbit(self):
        """Draw the complete orbital path of Moon with gap around current position"""
        if len(self.moon_positions) < 2:
            return
        
        # Calculate gap boundaries
        gap_start = max(0, self.current_frame - self.gap_frames)
        gap_end = min(len(self.moon_positions) - 1, self.current_frame + self.gap_frames)
        
        glLineWidth(0.8)
        glColor4f(0.8, 0.8, 0.8, 0.25)  # Gray with transparency
        
        # Draw segment before gap
        if gap_start > 0:
            glBegin(GL_LINE_STRIP)
            for i in range(0, gap_start + 1):
                x, y, z = self.moon_positions[i]
                glVertex3f(x, y, z)
            glEnd()
        
        # Draw segment after gap
        if gap_end < len(self.moon_positions) - 1:
            glBegin(GL_LINE_STRIP)
            for i in range(gap_end, len(self.moon_positions)):
                x, y, z = self.moon_positions[i]
                glVertex3f(x, y, z)
            glEnd()
        
    def draw_3d_label(self, text, x, y, z, color=(1.0, 1.0, 1.0)):
        """Draw a text label in 3D space"""
        if not hasattr(self, 'label_font'):
            self.label_font = pygame.font.SysFont('Arial', 14)
        
        # Render text to surface
        text_surface = self.label_font.render(text, True, (int(color[0]*255), int(color[1]*255), int(color[2]*255)))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # Billboard effect - make text face camera
        glRotatef(-self.rotation_z, 0, 0, 1)
        glRotatef(-self.rotation_x, 1, 0, 0)
        
        # Position text
        glRasterPos3f(0, 0, 0)
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                    GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        glPopMatrix()
    
    def draw_coordinate_axes(self):
        """Draw coordinate axes for reference"""
        glLineWidth(2.0)
        
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(2.0, 0, 0)
        
        # Y axis (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 2.0, 0)
        
        # Z axis (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 2.0)
        glEnd()
        
    def draw_info(self):
        """Draw information overlay"""
        # Save OpenGL state
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth test for text overlay
        glDisable(GL_DEPTH_TEST)
        
        # Create font if needed
        if not hasattr(self, 'font'):
            self.font = pygame.font.SysFont('Arial', 18)
            
        # Create text
        time_str = f"Time: {self.current_time.iso} UTC"
        frame_str = f"Frame {self.current_frame + 1}/{self.n_frames}"
        status_str = "Playing" if self.playing else "Paused"
        speed_str = f"Speed: {self.animation_speed}x"
        
        earth_dist = np.sqrt(self.earth_x**2 + self.earth_y**2 + self.earth_z**2)
        earth_dist_str = f"Earth-Sun: {earth_dist:.4f} AU"
        
        # Calculate Earth-Moon distance
        moon_earth_dx = self.moon_x_actual - self.earth_x
        moon_earth_dy = self.moon_y_actual - self.earth_y
        moon_earth_dz = self.moon_z_actual - self.earth_z
        earth_moon_dist = np.sqrt(moon_earth_dx**2 + moon_earth_dy**2 + moon_earth_dz**2)
        moon_dist_str = f"Earth-Moon: {earth_moon_dist * 149597870.7 / 1000:.0f} km"
        
        # Render text surfaces
        text_surface = self.font.render(time_str, True, (255, 255, 255))
        frame_surface = self.font.render(frame_str, True, (200, 200, 200))
        status_surface = self.font.render(status_str, True, (100, 255, 100) if self.playing else (255, 100, 100))
        speed_surface = self.font.render(speed_str, True, (200, 200, 200))
        earth_surface = self.font.render(earth_dist_str, True, (200, 200, 200))
        moon_surface = self.font.render(moon_dist_str, True, (200, 200, 200))
        
        # Draw text
        self._draw_text_surface(text_surface, 10, self.height - 30)
        self._draw_text_surface(frame_surface, 10, self.height - 55)
        self._draw_text_surface(status_surface, 10, self.height - 80)
        self._draw_text_surface(speed_surface, 10, self.height - 105)
        self._draw_text_surface(earth_surface, 10, self.height - 130)
        self._draw_text_surface(moon_surface, 10, self.height - 155)
        
        # Restore OpenGL state
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def _draw_text_surface(self, text_surface, x, y):
        """Draw a pygame text surface in OpenGL"""
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        glRasterPos2f(x, y)
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                    GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
    def render(self):
        """Render the scene"""
        # Get positions for current frame
        self.get_current_positions()
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Position camera above, looking down at the origin
        gluLookAt(0, 0, self.zoom,  # Eye position (above)
                  0, 0, 0,           # Look at origin
                  0, 1, 0)           # Up vector (Y is up)
        
        # Apply user rotations
        glRotatef(self.rotation_x, 1, 0, 0)  # Tilt
        glRotatef(self.rotation_z, 0, 0, 1)  # Rotate around Z
        
        # Draw coordinate axes (optional, for debugging)
        # self.draw_coordinate_axes()
        
        # Draw orbital paths first (background)
        self.draw_earth_orbit()
        self.draw_moon_orbit()
        
        # Draw celestial objects
        self.draw_earth_trail()
        self.draw_moon_trail()
        self.draw_sun()
        self.draw_earth()
        self.draw_moon()
        
        # Draw info overlay
        self.draw_info()
        
        # Swap buffers
        pygame.display.flip()
        
    def run(self):
        """Main rendering loop"""
        if not self.running:
            self.initialize()
        
        print("\nControls:")
        print("  Mouse drag: Rotate view")
        print("  Mouse wheel: Zoom in/out")
        print("  1/2/3: Zoom presets (Wide/Medium/Close)")
        print("  SPACE: Play/Pause")
        print("  UP/DOWN: Speed up/slow down")
        print("  LEFT/RIGHT: Step backward/forward")
        print("  R: Reset view")
        print("  ESC: Exit")
        print()
        
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)  # 60 FPS
            
        pygame.quit()
        print("Closed")


def main():
    """Entry point"""
    try:
        from PromptDate import prompt_date
        
        print("=== Solar System View - OpenGL ===")
        print("\nEnter animation parameters:")
        
        print("\nEnter animation start time:")
        start_time = prompt_date()
        
        print("\nEnter animation end time:")
        end_time = prompt_date()
        
        # Validate time range
        if end_time.jd <= start_time.jd:
            print("Error: End time must be after start time")
            sys.exit(1)
        
        # Prompt for frames per day
        while True:
            try:
                frames_input = input("\nFrames per day (default 12, range 1-288): ").strip()
                if frames_input == "":
                    frames_per_day = 12
                    break
                frames_per_day = int(frames_input)
                if 1 <= frames_per_day <= 288:
                    break
                print("Please enter a value between 1 and 288")
            except ValueError:
                print("Please enter a valid integer")
        
        duration_days = end_time.jd - start_time.jd
        total_frames = int(duration_days * frames_per_day)
        
        print(f"\nStart time: {start_time.iso} UTC")
        print(f"End time: {end_time.iso} UTC")
        print(f"Duration: {duration_days:.2f} days")
        print(f"Total frames: {total_frames}")
        
        # Create and run view
        view = SolarSystemView(start_time, end_time, frames_per_day, width=1200, height=900)
        view.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
