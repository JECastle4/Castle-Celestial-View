import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
import math
import numpy as np
import astropy.units as u

from PromptDate import prompt_date
from PromptLocation import prompt_location
from MoonPhase import moon_phase, moon_phase_angle
from astropy.time import Time
from astropy.coordinates import AltAz, get_sun, get_body, EarthLocation


def altaz_to_xy_polar(altitude, azimuth):
    """Convert altitude/azimuth to x/y coordinates for polar sky dome view.
    
    Parameters
    ----------
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
    
    # Normalize to 0-1 range (0=zenith, 1=horizon)2
    r = zenith_angle / 90.0
    
    # Convert azimuth to angle (North=90°, East=0°, South=270°, West=180° in standard math coords)
    # Azimuth 0°(N) → θ=90°, Azimuth 90°(E) → θ=0°, etc.
    theta_rad = np.radians(90.0 - azimuth)
    
    # Convert to Cartesian
    x = r * np.cos(theta_rad)
    y = r * np.sin(theta_rad)
    
    return x, y


def draw_moon_phase_indicator(ax, illumination_fraction, phase_angle, position=(0.85, 0.85), radius=0.1):
    """Draw a moon phase indicator showing the illuminated portion with proper terminator.
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to draw on.
    illumination_fraction : float
        Fraction of the moon that is illuminated (0.0 to 1.0).
    phase_angle : float
        Phase angle in degrees (0-360). 0-180=waxing, 180-360=waning.
    position : tuple
        (x, y) position in axes coordinates (0 to 1).
    radius : float
        Radius of the indicator in axes coordinates.
    
    Returns
    -------
    patches : list
        List of patch objects created.
    texts : list
        List of text objects created.
    """
    x, y = position
    created_patches = []
    created_texts = []
    
    # Determine if waxing or waning
    is_waxing = phase_angle < 180
    
    # Draw background circle (dark)
    moon_bg = patches.Circle((x, y), radius, color='#222222', ec='gray', 
                            linewidth=1.5, transform=ax.transAxes, zorder=100)
    ax.add_patch(moon_bg)
    created_patches.append(moon_bg)
    
    # Draw inner circle representing illumination percentage
    if illumination_fraction > 0.01:
        inner_radius = radius * illumination_fraction
        moon_lit = patches.Circle((x, y), inner_radius, color='lightgray', 
                                 transform=ax.transAxes, zorder=101)
        ax.add_patch(moon_lit)
        created_patches.append(moon_lit)
    
    # Add percentage text in center
    text1 = ax.text(x, y, f'{illumination_fraction*100:.0f}%', 
           ha='center', va='center', color='white', fontsize=9, weight='bold',
           transform=ax.transAxes, zorder=103)
    text2 = ax.text(x, y - radius - 0.03, 'Moon Phase', 
           ha='center', va='top', color='white', fontsize=7, alpha=0.7,
           transform=ax.transAxes, zorder=103)
    created_texts.extend([text1, text2])
    
    return created_patches, created_texts


def plot_sky_view(location, time):
    """Plot Sun and Moon positions in a full hemispherical sky dome view.
    
    Parameters
    ----------
    location : EarthLocation
        Observer location.
    time : Time
        Observation time (UTC).
    """
    # Calculate positions
    altaz_frame = AltAz(obstime=time, location=location)
    sun = get_sun(time).transform_to(altaz_frame)
    moon = get_body('moon', time, location=location).transform_to(altaz_frame)
    
    sun_alt = sun.alt.deg
    sun_az = sun.az.deg
    moon_alt = moon.alt.deg
    moon_az = moon.az.deg
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.canvas.manager.set_window_title(f'Sky Dome View for {time.iso} UTC at Location ({location.lat.deg:.2f}°, {location.lon.deg:.2f}°)')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect('equal')
    ax.set_facecolor('#000033')  # Dark blue sky
    
    # Draw horizon circle
    horizon = patches.Circle((0, 0), 1.0, fill=True, facecolor='#001a33', 
                            edgecolor='white', linewidth=2, alpha=0.5, zorder=1)
    ax.add_patch(horizon)
    
    # Draw altitude circles (30°, 60°)
    for alt_deg in [30, 60]:
        zenith_angle = 90 - alt_deg
        radius = zenith_angle / 90.0
        circle = patches.Circle((0, 0), radius, fill=False, edgecolor='white', 
                               linewidth=0.5, linestyle='--', alpha=0.3, zorder=2)
        ax.add_patch(circle)
        # Label
        ax.text(0.02, radius, f'{alt_deg}°', color='white', fontsize=8, alpha=0.5, zorder=3)
    
    # Draw cardinal direction lines
    ax.plot([0, 0], [0, 1], 'w-', linewidth=0.5, alpha=0.3, zorder=2)  # N
    ax.plot([0, 0], [0, -1], 'w-', linewidth=0.5, alpha=0.3, zorder=2)  # S
    ax.plot([-1, 0], [0, 0], 'w-', linewidth=0.5, alpha=0.3, zorder=2)  # E
    ax.plot([0, 1], [0, 0], 'w-', linewidth=0.5, alpha=0.3, zorder=2)  # W
    
    # Label cardinal directions (outside the horizon circle)
    ax.text(0, 1.15, 'N', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(0, -1.15, 'S', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(-1.15, 0, 'E', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(1.15, 0, 'W', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    
    # Label zenith at center
    ax.text(0, 0, '⊕', ha='center', va='center', color='white', fontsize=12, alpha=0.4, zorder=3)
    
    # Create horizon clip path (only show objects above horizon)
    horizon_clip = patches.Circle((0, 0), 1.0, transform=ax.transData)
    
    # Plot Sun if above horizon
    if sun_alt > 0:
        sun_x, sun_y = altaz_to_xy_polar(sun_alt, sun_az)
        # Glow halo (illumination effect)
        sun_glow = patches.Circle((sun_x, sun_y), 0.08, color='yellow', alpha=0.3, zorder=8)
        sun_glow.set_clip_path(horizon_clip)
        ax.add_patch(sun_glow)
        # Accurate angular size (~0.5° diameter → ~0.0028 radius at this scale)
        sun_accurate = patches.Circle((sun_x, sun_y), 0.0028, color='yellow', ec='orange', 
                                     linewidth=0.5, zorder=10)
        sun_accurate.set_clip_path(horizon_clip)
        ax.add_patch(sun_accurate)
        # Position label to avoid overlap with glow
        label_offset = 0.18 if sun_y > 0 else -0.18
        ax.text(sun_x, sun_y + label_offset, f'☉\n{sun_alt:.1f}°', 
                ha='center', va='center', color='yellow', fontsize=10, weight='bold', zorder=11)
    
    # Plot Moon if above horizon
    if moon_alt > 0:
        moon_x, moon_y = altaz_to_xy_polar(moon_alt, moon_az)
        # Glow halo (illumination effect)
        moon_glow = patches.Circle((moon_x, moon_y), 0.06, color='lightgray', alpha=0.3, zorder=8)
        moon_glow.set_clip_path(horizon_clip)
        ax.add_patch(moon_glow)
        # Accurate angular size (~0.5° diameter → ~0.0028 radius at this scale)
        moon_accurate = patches.Circle((moon_x, moon_y), 0.0028, color='lightgray', ec='white', 
                                      linewidth=0.5, zorder=10)
        moon_accurate.set_clip_path(horizon_clip)
        ax.add_patch(moon_accurate)
        # Position label
        label_offset = 0.15 if moon_y > 0 else -0.15
        ax.text(moon_x, moon_y + label_offset, f'☾\n{moon_alt:.1f}°', 
                ha='center', va='center', color='lightgray', fontsize=10, weight='bold', zorder=11)
        
        # Draw moon phase indicator when moon is visible
        illumination = moon_phase(time, location=location)
        phase_angle = moon_phase_angle(time, location=location)
        if moon_alt > 0:  # Only show when moon is above horizon
            draw_moon_phase_indicator(ax, illumination, phase_angle)
    
    ax.axis('off')
    plt.title(f'Full Sky Dome View\n{time.iso} UTC\nLat: {location.lat.deg:.2f}°, Lon: {location.lon.deg:.2f}°', 
              color='white', fontsize=14, pad=20)
    plt.tight_layout()
    plt.show()


def animate_day(location, date):
    """Animate Sun and Moon positions over a 24-hour period.
    
    Parameters
    ----------
    location : EarthLocation
        Observer location.
    date : Time
        Reference date (will animate from midnight to midnight UTC).
    """
    # Start at midnight UTC on the given date
    midnight_jd = math.floor(date.jd)
    midnight = Time(midnight_jd, format='jd', scale='utc')
    
    # Calculate moon phase (at start of animation)
    moon_illumination = moon_phase(midnight, location=location)
    moon_phase_ang = moon_phase_angle(midnight, location=location)
    
    # Create time array for 24 hours (every 5 minutes = 288 frames)
    n_frames = 288
    times = midnight + np.linspace(0, 24, n_frames) * u.hour
    
    # Pre-calculate all positions for efficiency
    sun_positions = []
    moon_positions = []
    moon_illuminations = []
    moon_phase_angles = []
    
    for t in times:
        altaz_frame = AltAz(obstime=t, location=location)
        sun = get_sun(t).transform_to(altaz_frame)
        moon = get_body('moon', t, location=location).transform_to(altaz_frame)
        sun_positions.append((sun.alt.deg, sun.az.deg))
        moon_positions.append((moon.alt.deg, moon.az.deg))
        
        # Calculate moon phase for each frame
        moon_illuminations.append(moon_phase(t, location=location))
        moon_phase_angles.append(moon_phase_angle(t, location=location))
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.canvas.manager.set_window_title(f'Sky Dome View 24 hours from {midnight.iso} UTC at Location ({location.lat.deg:.2f}°, {location.lon.deg:.2f}°)')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect('equal')
    ax.set_facecolor('#000033')
    
    # Draw static elements
    horizon = patches.Circle((0, 0), 1.0, fill=True, facecolor='#001a33', 
                            edgecolor='white', linewidth=2, alpha=0.5, zorder=1)
    ax.add_patch(horizon)
    
    # Altitude circles
    for alt_deg in [30, 60]:
        zenith_angle = 90 - alt_deg
        radius = zenith_angle / 90.0
        circle = patches.Circle((0, 0), radius, fill=False, edgecolor='white', 
                               linewidth=0.5, linestyle='--', alpha=0.3, zorder=2)
        ax.add_patch(circle)
        ax.text(0.02, radius, f'{alt_deg}°', color='white', fontsize=8, alpha=0.5, zorder=3)
    
    # Cardinal lines
    ax.plot([0, 0], [0, 1], 'w-', linewidth=0.5, alpha=0.3, zorder=2)
    ax.plot([0, 0], [0, -1], 'w-', linewidth=0.5, alpha=0.3, zorder=2)
    ax.plot([-1, 0], [0, 0], 'w-', linewidth=0.5, alpha=0.3, zorder=2)
    ax.plot([0, 1], [0, 0], 'w-', linewidth=0.5, alpha=0.3, zorder=2)
    
    # Cardinal labels
    ax.text(0, 1.15, 'N', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(0, -1.15, 'S', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(-1.15, 0, 'E', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(1.15, 0, 'W', ha='center', va='center', color='white', fontsize=16, weight='bold', zorder=5)
    ax.text(0, 0, '⊕', ha='center', va='center', color='white', fontsize=12, alpha=0.4, zorder=3)
    
    # Create horizon clip path (only show objects above horizon)
    horizon_clip = patches.Circle((0, 0), 1.0, transform=ax.transData)
    
    # Create animated elements
    # Sun: glow halo + accurate size
    sun_glow = patches.Circle((0, 0), 0.08, color='yellow', alpha=0.3, zorder=8, visible=False)
    sun_glow.set_clip_path(horizon_clip)
    sun_circle = patches.Circle((0, 0), 0.0028, color='yellow', ec='orange', linewidth=0.5, zorder=10, visible=False)
    sun_circle.set_clip_path(horizon_clip)
    ax.add_patch(sun_glow)
    ax.add_patch(sun_circle)
    
    # Moon: glow halo + accurate size
    moon_glow = patches.Circle((0, 0), 0.06, color='lightgray', alpha=0.3, zorder=8, visible=False)
    moon_glow.set_clip_path(horizon_clip)
    moon_circle = patches.Circle((0, 0), 0.0028, color='lightgray', ec='white', linewidth=0.5, zorder=10, visible=False)
    moon_circle.set_clip_path(horizon_clip)
    ax.add_patch(moon_glow)
    ax.add_patch(moon_circle)
    
    # Moon phase indicator (will be updated in animation to show/hide)
    moon_phase_patches = []  # Store list of patches for the moon phase indicator
    moon_phase_texts = []    # Store list of text objects for the moon phase indicator
    
    sun_label = ax.text(0, 0, '', ha='center', va='center', color='yellow', fontsize=10, weight='bold', zorder=11)
    moon_label = ax.text(0, 0, '', ha='center', va='center', color='lightgray', fontsize=10, weight='bold', zorder=11)
    
    # Time display
    time_text = ax.text(0, -1.25, '', ha='center', va='top', color='white', fontsize=12, zorder=5)
    
    # Path trails
    sun_trail, = ax.plot([], [], 'y-', linewidth=1, alpha=0.3, zorder=4)
    moon_trail, = ax.plot([], [], color='lightgray', linewidth=1, alpha=0.3, zorder=4)
    
    ax.axis('off')
    title = ax.text(0.5, 0.98, f'Full Sky Dome - 24 Hour Animation\nLat: {location.lat.deg:.2f}°, Lon: {location.lon.deg:.2f}°',
                   ha='center', va='top', transform=fig.transFigure, color='white', fontsize=14)
    
    def update(frame):
        """Update animation frame."""
        nonlocal moon_phase_patches, moon_phase_texts
        
        sun_alt, sun_az = sun_positions[frame]
        moon_alt, moon_az = moon_positions[frame]
        current_time = times[frame]
        
        # Collect trail points (only visible positions)
        sun_trail_x, sun_trail_y = [], []
        moon_trail_x, moon_trail_y = [], []
        
        for i in range(max(0, frame - 30), frame + 1):  # Show last 30 points (~2.5 hours)
            alt, az = sun_positions[i]
            if alt > 0:
                x, y = altaz_to_xy_polar(alt, az)
                sun_trail_x.append(x)
                sun_trail_y.append(y)
            
            alt, az = moon_positions[i]
            if alt > 0:
                x, y = altaz_to_xy_polar(alt, az)
                moon_trail_x.append(x)
                moon_trail_y.append(y)
        
        sun_trail.set_data(sun_trail_x, sun_trail_y)
        moon_trail.set_data(moon_trail_x, moon_trail_y)
        
        # Update Sun
        if sun_alt > 0:
            sun_x, sun_y = altaz_to_xy_polar(sun_alt, sun_az)
            sun_glow.center = (sun_x, sun_y)
            sun_glow.set_visible(True)
            sun_circle.center = (sun_x, sun_y)
            sun_circle.set_visible(True)
            label_offset = 0.18 if sun_y > 0 else -0.18
            sun_label.set_position((sun_x, sun_y + label_offset))
            sun_label.set_text(f'☉\n{sun_alt:.0f}°')
            sun_label.set_visible(True)
        else:
            sun_glow.set_visible(False)
            sun_circle.set_visible(False)
            sun_label.set_visible(False)
        
        # Update Moon
        if moon_alt > 0:
            moon_x, moon_y = altaz_to_xy_polar(moon_alt, moon_az)
            moon_glow.center = (moon_x, moon_y)
            moon_glow.set_visible(True)
            moon_circle.center = (moon_x, moon_y)
            moon_circle.set_visible(True)
            label_offset = 0.15 if moon_y > 0 else -0.15
            moon_label.set_position((moon_x, moon_y + label_offset))
            moon_label.set_text(f'☾\n{moon_alt:.0f}°')
            moon_label.set_visible(True)
            
            # Update moon phase indicator when moon is visible
            # Remove old indicator if it exists
            for patch in moon_phase_patches:
                patch.remove()
            for text in moon_phase_texts:
                text.remove()
            moon_phase_patches.clear()
            moon_phase_texts.clear()
            
            # Create new indicator with updated phase
            patch_list, text_list = draw_moon_phase_indicator(ax, moon_illuminations[frame], moon_phase_angles[frame])
            moon_phase_patches.extend(patch_list)
            moon_phase_texts.extend(text_list)
        else:
            moon_glow.set_visible(False)
            moon_circle.set_visible(False)
            moon_label.set_visible(False)
            
            # Hide moon phase indicator when moon is not visible
            if moon_phase_patches:
                # Remove all phase indicator patches and texts
                for patch in moon_phase_patches:
                    patch.remove()
                for text in moon_phase_texts:
                    text.remove()
                moon_phase_patches.clear()
                moon_phase_texts.clear()
        
        # Update time display
        time_text.set_text(f'{current_time.iso.split()[1][:5]} UTC')
        
        # Return all artists to be redrawn (needed for blit=True)
        artists = [sun_glow, sun_circle, moon_glow, moon_circle, sun_label, moon_label, time_text, sun_trail, moon_trail]
        artists.extend(moon_phase_patches)
        artists.extend(moon_phase_texts)
        return artists
    
    # Create animation (5 minutes per frame, ~60ms interval for smooth playback)
    anim = FuncAnimation(fig, update, frames=n_frames, interval=60, blit=True, repeat=True)
    
    plt.tight_layout()
    plt.show()


def main():
    """Get location and time, then animate 24-hour sky view."""
    t = prompt_date()
    loc = prompt_location()
    
    # Uncomment to show static view at specific time:
    # plot_sky_view(loc, t)
    
    # Animate full day
    animate_day(loc, t)


if __name__ == "__main__":
    main()
