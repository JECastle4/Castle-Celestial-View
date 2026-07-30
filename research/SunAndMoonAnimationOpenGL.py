"""
Sun and Moon Animation using OpenGL
Sky dome view with sun and moon tracking
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import sys
import math
import warnings
from astropy.time import Time
from astropy.coordinates import AltAz, get_sun, get_body, EarthLocation
import astropy.units as u
from astropy.utils.exceptions import AstropyWarning

from PromptDate import prompt_date
from PromptLocation import prompt_location
from MoonPhase import moon_phase, moon_phase_angle, moon_phase_name


class SkyDomeView:
    """OpenGL-based sky dome visualization"""
    
    def __init__(self, location, start_time, end_time, frames_per_day=12, width=800, height=800):
        """Initialize the sky dome view
        
        Parameters
        ----------
        location : EarthLocation
            Observer location
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
        
        # Observation parameters
        self.location = location
        self.start_time = start_time
        self.end_time = end_time
        self.frames_per_day = frames_per_day
        
        # Animation parameters
        self.current_frame = 0
        self.playing = True
        self.animation_speed = 1  # Frames per render cycle
        
        # Pre-calculate all positions for the time range
        self._setup_animation()
        
        # View control
        self.rotation_x = 0  # Tilt
        self.rotation_z = 0  # Rotation
        self.zoom = 2.5      # Camera distance
        
    def _setup_animation(self):
        """Pre-calculate sun and moon positions for the specified time range"""
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
        self.sun_positions = []  # List of (alt, az) tuples
        self.moon_positions = []  # List of (alt, az) tuples
        self.moon_illuminations = []  # List of illumination fractions
        self.moon_phase_angles = []  # List of phase angles
        self.moon_phase_names = []  # List of phase names
        
        # Suppress expected coordinate transformation warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', AstropyWarning)
            
            for i, t in enumerate(self.times):
                # Show progress
                if i % max(1, self.n_frames // 100) == 0 or i == self.n_frames - 1:
                    percent = (i + 1) / self.n_frames * 100
                    print(f"\rProgress: {i + 1}/{self.n_frames} ({percent:.1f}%)", end='', flush=True)
                
                altaz_frame = AltAz(obstime=t, location=self.location)
                
                # Sun position
                sun = get_sun(t).transform_to(altaz_frame)
                self.sun_positions.append((sun.alt.deg, sun.az.deg))
                
                # Moon position
                moon = get_body('moon', t, location=self.location).transform_to(altaz_frame)
                self.moon_positions.append((moon.alt.deg, moon.az.deg))
                
                # Moon phase
                self.moon_illuminations.append(moon_phase(t, location=self.location))
                self.moon_phase_angles.append(moon_phase_angle(t, location=self.location))
                self.moon_phase_names.append(moon_phase_name(t, location=self.location))
        
        print()  # New line after progress
        print(f"Animation setup complete!")
        print(f"Time range: {self.times[0].iso} to {self.times[-1].iso} UTC")
        
    def get_current_positions(self):
        """Get sun and moon positions for current frame"""
        self.sun_alt, self.sun_az = self.sun_positions[self.current_frame]
        self.moon_alt, self.moon_az = self.moon_positions[self.current_frame]
        self.moon_illumination = self.moon_illuminations[self.current_frame]
        self.moon_phase_angle = self.moon_phase_angles[self.current_frame]
        self.moon_phase_name_str = self.moon_phase_names[self.current_frame]
        self.current_time = self.times[self.current_frame]
        
    @staticmethod
    def altaz_to_xy_polar(altitude, azimuth):
        """Convert altitude/azimuth to x/y coordinates for polar sky dome view.
        
        Parameters
        ----------52
        altitude : float
            Altitude in degrees (0=horizon, 90=zenith).
        azimuth : float
            Azimuth in degrees (0=N, 90=E, 180=S, 270=W).
        
        Returns
        -------
        tuple (x, y)
            Cartesian coordinates where:
            - center (0,0) = zenith
            - radius 1 = horizon
            - North = top (y=1), East = left (x=-1), South = bottom (y=-1), West = right (x=1)
        """
        # Zenith angle (angular distance from zenith)
        zenith_angle = 90.0 - altitude
        
        # Normalize to 0-1 range (0=zenith, 1=horizon)
        r = zenith_angle / 90.0
        
        # Convert azimuth to angle (North=90°, East=0°, South=270°, West=180° in standard math coords)
        theta_rad = np.radians(90.0 - azimuth)
        
        # Convert to Cartesian
        x = r * np.cos(theta_rad)
        y = r * np.sin(theta_rad)
        
        return x, y
        
    def initialize(self):
        """Initialize pygame and OpenGL"""
        pygame.init()
        
        # Set up display with OpenGL
        self.display = pygame.display.set_mode(
            (self.width, self.height),
            DOUBLEBUF | OPENGL
        )
        
        # Set window title with location info
        title = f"Sky Dome View - Lat: {self.location.lat.deg:.2f}°, Lon: {self.location.lon.deg:.2f}°"
        pygame.display.set_caption(title)
        
        # Initialize OpenGL
        self._init_opengl()
        
        # Create clock for frame rate control
        self.clock = pygame.time.Clock()
        self.running = True
        
        print("OpenGL Sky Dome initialized")
        print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        
    def _init_opengl(self):
        """Configure OpenGL rendering"""
        # Background color (dark blue for night sky)
        glClearColor(0.0, 0.0, 0.2, 1.0)  # Dark blue
        
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        
        # Enable smooth lines
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Enable lighting for 3D moon phase
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
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
                    self.zoom = 2.5
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
                    print(f"Frame {self.current_frame}/{self.n_frames}")
                elif event.key == pygame.K_RIGHT:
                    # Step forward
                    self.current_frame = (self.current_frame + 1) % self.n_frames
                    print(f"Frame {self.current_frame}/{self.n_frames}")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    self.zoom = max(1.5, self.zoom - 0.2)
                elif event.button == 5:  # Mouse wheel down
                    self.zoom = min(5.0, self.zoom + 0.2)
        
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
            
    def draw_circle(self, radius, segments=64, filled=False):
        """Draw a circle in the XY plane"""
        if filled:
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, 0, 0)
        else:
            glBegin(GL_LINE_LOOP)
            
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            glVertex3f(x, y, 0)
        glEnd()
        
    def draw_horizon_circle(self):
        """Draw the main horizon circle (radius = 1.0)"""
        # Filled circle for background
        glColor4f(0.0, 0.1, 0.2, 0.5)  # Dark blue, semi-transparent
        self.draw_circle(1.0, segments=128, filled=True)
        
        # Border
        glLineWidth(2.0)
        glColor3f(1.0, 1.0, 1.0)  # White
        self.draw_circle(1.0, segments=128, filled=False)
        
    def draw_altitude_circles(self):
        """Draw altitude reference circles at 30° and 60°"""
        glLineWidth(1.0)
        glColor4f(1.0, 1.0, 1.0, 0.3)  # White, semi-transparent
        
        # 60° altitude (30° from zenith) -> radius = 30/90 = 0.333
        self.draw_circle(0.333, segments=64)
        
        # 30° altitude (60° from zenith) -> radius = 60/90 = 0.667
        self.draw_circle(0.667, segments=64)
        
    def draw_cardinal_lines(self):
        """Draw lines to cardinal directions"""
        glLineWidth(1.0)
        glColor4f(1.0, 1.0, 1.0, 0.3)  # White, semi-transparent
        
        glBegin(GL_LINES)
        # North (top, +Y)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1.0, 0)
        # South (bottom, -Y)
        glVertex3f(0, 0, 0)
        glVertex3f(0, -1.0, 0)
        # East (left, -X)
        glVertex3f(0, 0, 0)
        glVertex3f(-1.0, 0, 0)
        # West (right, +X)
        glVertex3f(0, 0, 0)
        glVertex3f(1.0, 0, 0)
        glEnd()
        
    def draw_sun(self):
        """Draw the sun if above horizon"""
        if self.sun_alt <= 0:
            return  # Sun is below horizon
            
        x, y = self.altaz_to_xy_polar(self.sun_alt, self.sun_az)
        
        # Draw glow halo
        glColor4f(1.0, 1.0, 0.0, 0.3)  # Yellow, semi-transparent
        self.draw_filled_circle(x, y, 0.08, z=0.01, segments=32)
        
        # Draw sun disk
        glColor3f(1.0, 1.0, 0.0)  # Bright yellow
        self.draw_filled_circle(x, y, 0.02, z=0.01, segments=32)
        
        # Draw border
        glLineWidth(1.5)
        glColor3f(1.0, 0.5, 0.0)  # Orange
        self.draw_circle_at(x, y, 0.02, z=0.01, segments=32)
        
    def draw_moon(self):
        """Draw the moon if above horizon"""
        if self.moon_alt <= 0:
            return  # Moon is below horizon
            
        x, y = self.altaz_to_xy_polar(self.moon_alt, self.moon_az)
        
        # Draw glow halo
        glColor4f(0.8, 0.8, 0.8, 0.3)  # Gray, semi-transparent
        self.draw_filled_circle(x, y, 0.06, z=0.02, segments=32)
        
        # Draw moon disk
        glColor3f(0.9, 0.9, 0.9)  # Light gray
        self.draw_filled_circle(x, y, 0.02, z=0.02, segments=32)
        
        # Draw border
        glLineWidth(1.5)
        glColor3f(1.0, 1.0, 1.0)  # White
        self.draw_circle_at(x, y, 0.02, z=0.02, segments=32)
        
    def draw_circle_at(self, cx, cy, radius, z=0.0, segments=32):
        """Draw a circle at specific position"""
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            glVertex3f(x, y, z)
        glEnd()
        
    def draw_filled_circle(self, cx, cy, radius, z=0.0, segments=32):
        """Draw a filled circle at specific position"""
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(cx, cy, z)  # Center
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            glVertex3f(x, y, z)
        glEnd()
        
    def draw_moon_phase_indicator(self):
        """Draw a 3D moon phase indicator in the top-right corner"""
        # Only draw if moon data is available
        if not hasattr(self, 'moon_illumination'):
            return
            
        # Save current state
        glPushMatrix()
        
        # Disable lighting for the sky view, enable for 3D moon
        glDisable(GL_LIGHTING)
        
        # Set up viewport for indicator (top-right corner)
        glViewport(self.width - 150, self.height - 150, 140, 140)
        
        # Set up orthographic projection for the indicator
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(-2, 2, -2, 2, -10, 10)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Position camera for 3D moon
        gluLookAt(0, 0, 5,  # Eye position
                  0, 0, 0,  # Look at
                  0, 1, 0)  # Up vector
        
        # Enable lighting for the 3D moon sphere
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # Calculate light direction based on phase angle
        # Phase angle: 0° = new moon (sun behind moon from Earth), 180° = full moon (sun in front)
        # Camera is at [0, 0, 5] looking at [0, 0, 0]
        # At full moon (180°), light should come from camera side (positive Z)
        # At new moon (0°), light should come from opposite side (negative Z)
        phase_rad = np.radians(self.moon_phase_angle)
        
        # Light position based on phase angle (inverted from apparent phase angle)
        # We rotate around Y axis (vertical)
        light_x = -np.sin(phase_rad)  # Negative to invert
        light_z = -np.cos(phase_rad)  # Negative to invert
        light_pos = [light_x * 10, 0.0, light_z * 10, 0.0]  # Directional light (w=0)
        
        # Set up light properties
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        
        # Draw the moon sphere
        glColor3f(0.7, 0.7, 0.7)  # Gray color for moon
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, 1.0, 32, 32)
        gluDeleteQuadric(quadric)
        
        # Disable lighting for text
        glDisable(GL_LIGHTING)
        
        # Restore projection
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        # Restore viewport
        glViewport(0, 0, self.width, self.height)
        
        glPopMatrix()
        
    def draw_time_display(self):
        """Draw time and frame info as text overlay"""
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
        
        # Create text
        if not hasattr(self, 'font'):
            self.font = pygame.font.SysFont('Arial', 18)
            self.font_small = pygame.font.SysFont('Arial', 14)
            
        time_str = f"{self.current_time.iso} UTC"
        frame_str = f"Frame {self.current_frame + 1}/{self.n_frames}"
        status_str = "Playing" if self.playing else "Paused"
        speed_str = f"Speed: {self.animation_speed}x"
        
        # Moon phase info (top-right, above the 3D indicator)
        phase_percent_str = f"{self.moon_illumination * 100:.1f}%"
        phase_name_str = self.moon_phase_name_str
        
        # Render text surfaces
        text_surface = self.font.render(time_str, True, (255, 255, 255))
        frame_surface = self.font.render(frame_str, True, (200, 200, 200))
        status_surface = self.font.render(status_str, True, (100, 255, 100) if self.playing else (255, 100, 100))
        speed_surface = self.font.render(speed_str, True, (200, 200, 200))
        
        # Moon phase surfaces (smaller font, right-aligned)
        phase_percent_surface = self.font.render(phase_percent_str, True, (220, 220, 220))
        phase_name_surface = self.font_small.render(phase_name_str, True, (200, 200, 200))
        
        # Convert to OpenGL texture and draw (left side)
        self._draw_text_surface(text_surface, 10, self.height - 30)
        self._draw_text_surface(frame_surface, 10, self.height - 55)
        self._draw_text_surface(status_surface, 10, self.height - 80)
        self._draw_text_surface(speed_surface, 10, self.height - 105)
        
        # Draw moon phase info above the 3D indicator (right-aligned)
        # The 3D indicator is at position (width-150, height-150) with size 140x140
        # So we want text above that, around y = height - 10
        phase_percent_x = self.width - 10 - phase_percent_surface.get_width()
        phase_name_x = self.width - 10 - phase_name_surface.get_width()
        
        self._draw_text_surface(phase_percent_surface, phase_percent_x, self.height - 20)
        self._draw_text_surface(phase_name_surface, phase_name_x, self.height - 40)
        
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
        
        # Position camera
        glTranslatef(0.0, 0.0, -self.zoom)
        
        # Apply rotations
        glRotatef(self.rotation_x, 1, 0, 0)  # Tilt up/down
        glRotatef(self.rotation_z, 0, 0, 1)  # Rotate around Z
        
        # Draw sky dome elements
        self.draw_horizon_circle()
        self.draw_altitude_circles()
        self.draw_cardinal_lines()
        
        # Draw celestial objects
        self.draw_sun()
        self.draw_moon()
        
        # Draw moon phase indicator in corner
        self.draw_moon_phase_indicator()
        
        # Display time
        self.draw_time_display()
        
        # Swap buffers
        pygame.display.flip()
        
    def run(self):
        """Main rendering loop"""
        if not self.running:
            self.initialize()
        
        print("\nControls:")
        print("  Mouse drag: Rotate view")
        print("  Mouse wheel: Zoom in/out")
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
        # Prompt for location and time
        print("=== Sky Dome View - OpenGL ===")
        print("\nEnter observation parameters:")
        
        location = prompt_location()
        
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
        
        print(f"\nLocation: Lat={location.lat.deg:.4f}°, Lon={location.lon.deg:.4f}°, Height={location.height.value:.1f}m")
        print(f"Start time: {start_time.iso} UTC")
        print(f"End time: {end_time.iso} UTC")
        print(f"Duration: {duration_days:.2f} days")
        print(f"Total frames: {total_frames}")
        
        # Create and run view
        view = SkyDomeView(location, start_time, end_time, frames_per_day, width=800, height=800)
        view.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
