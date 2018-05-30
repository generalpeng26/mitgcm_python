#######################################################
# Zonal or meridional slices (lat-depth or lon-depth)
#######################################################

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import sys

from grid import Grid
from io import read_netcdf, find_variable
from utils import mask_3d
from plot_utils import slice_patches, plot_slice_patches, finished_plot, slice_axes, plusminus_cmap, lon_label, lat_label, parse_date, get_extend
from diagnostics import t_minus_tf


# Basic slice plot of any variable.

# Arguments:
# data: 3D (depth x lat x lon) array of data to plot, already masked with mask_3d
# grid: Grid object

# Optional keyword arguments:
# gtype: as in function Grid.get_lon_lat
# lon0, lat0: as in function slice_patches
# hmin, hmax, zmin, zmax: as in function slice_patches
# vmin, vmax: desired min and max values for colour map
# ctype: 'basic' or 'plusminus', as in function set_colours
# title: a title to add to the plot (not including lon0 or lat0, this will be added)
# date_string: as in function latlon_plot
# fig_name: as in function finished_plot

def slice_plot (data, grid, gtype='t', lon0=None, lat0=None, hmin=None, hmax=None, zmin=None, zmax=None, vmin=None, vmax=None, ctype='basic', title=None, date_string=None, fig_name=None):

    # Choose what the endpoints of the colourbar should do
    extend = get_extend(vmin=vmin, vmax=vmax)

    # Build the patches and get the bounds
    patches, values, loc0, hmin_tmp, hmax_tmp, zmin_tmp, zmax_tmp, vmin_tmp, vmax_tmp = slice_patches(data, grid, gtype=gtype, lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax)
    
    # Bit of padding on the left and bottom to show mask
    hmin_tmp -= 0.015*(hmax_tmp-hmin_tmp)
    zmin_tmp -= 0.015*(zmax_tmp-zmin_tmp)
    # Update any bounds which aren't already set
    if hmin is None:
        hmin = hmin_tmp
    if hmax is None:
        hmax = hmax_tmp
    if zmin is None:
        zmin = zmin_tmp
    if zmax is None:
        zmax = zmax_tmp
    if vmin is None:
        vmin = vmin_tmp
    if vmax is None:
        vmax = vmax_tmp
    # Set colour map
    if ctype == 'basic':
        cmap = 'jet'
    elif ctype == 'plusminus':
        cmap = plusminus_cmap(vmin, vmax)
    else:
        print 'Error (slice_plot): invalid ctype=' + ctype
        sys.exit()

    # Figure out orientation and format slice location
    if lon0 is not None:
        h_axis = 'lat'
        loc_string = lon_label(loc0, 3)
    elif lat0 is not None:
        h_axis = 'lon'
        loc_string = lat_label(loc0, 3)
    # Set up the title
    if title is None:
        title = ''
    title += ' at ' + loc_string    

    # Plot
    fig, ax = plt.subplots()
    # Add patches
    img = plot_slice_patches(ax, patches, values, hmin, hmax, zmin, zmax, vmin, vmax, cmap=cmap)
    # Make nice axis labels
    slice_axes(ax, h_axis=h_axis)
    # Add a colourbar
    plt.colorbar(img, extend=extend)
    # Add a title
    plt.title(title, fontsize=18)
    if date_string is not None:
        # Add the date in the bottom right corner
        plt.text(.99, .01, date_string, fontsize=14, ha='right', va='bottom', transform=fig.transFigure)
    finished_plot(fig, fig_name=fig_name)


# NetCDF interface. Call this function with a specific variable key and information about the necessary NetCDF file, to get a nice slice plot.

# Arguments:
# var: keyword indicating which special variable to plot. The options are:
#      'temp': temperature
#      'salt': salinity
#      'tminustf': difference from in-situ freezing point
#      'u': zonal velocity
#      'v': meridional velocity
# file_path: path to NetCDF file containing the necessary variable:
#      'temp': THETA
#      'salt': SALT
#      'tminustf': THETA and SALT
#      'u': 'UVEL'
#      'v': 'VVEL'
# If there are two variables needed (eg THETA and SALT for 'tminustf') and they are stored in separate files, you can put the other file in second_file_path (see below).
# grid: either a Grid object, or the path to the NetCDF grid file

# Optional keyword arguments:
# lon0, lat0: as in function slice_patches
# time_index, t_start, t_end, time_average: as in function read_netcdf. You must either define time_index or set time_average=True, so it collapses to a single record.
# hmin, hmax, zmin, zmax: as in function slice_patches
# vmin, vmax: as in function slice_plot
# date_string: as in function slice_plot. If time_index is defined and date_string isn't, date_string will be automatically determined based on the calendar in file_path.
# fig_name: as in function finished_plot
# second_file_path: path to NetCDF file containing a second variable which is necessary and not contained in file_path. It doesn't matter which is which.

def read_plot_slice (var, file_path, grid, lon0=None, lat0=None, time_index=None, t_start=None, t_end=None, time_average=False, hmin=None, hmax=None, zmin=None, zmax=None, vmin=None, vmax=None, date_string=None, fig_name=None, second_file_path=None):

    # Make sure we'll end up with a single record in time
    if time_index is None and not time_average:
        print 'Error (read_plot_slice): either specify time_index or set time_average=True.'
        sys.exit()

    if date_string is None and time_index is not None:
        # Determine what to write about the date
        date_string = parse_date(file_path=file_path, time_index=time_index)

    if not isinstance(grid, Grid):
        # This is the path to the NetCDF grid file, not a Grid object
        # Make a grid object from it
        grid = Grid(grid)

    # Read necessary variables from NetCDF file and mask appropriately
    if var in ['temp', 'tminustf']:
        # Read temperature. Some of these variables need more than temperature and so second_file_path might be set.
        if second_file_path is not None:
            file_path_use = find_variable(file_path, second_file_path, 'THETA')
        else:
            file_path_use = file_path        
        temp = mask_3d(read_netcdf(file_path_use, 'THETA', time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average), grid)
    if var in ['salt', 'tminustf']:
        if second_file_path is not None:
            file_path_use = find_variable(file_path, second_file_path, 'SALT')
        else:
            file_path_use = file_path
        salt = mask_3d(read_netcdf(file_path_use, 'SALT', time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average), grid)
    if var == 'u':
        u = mask_3d(read_netcdf(file_path, 'UVEL', time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average), grid, gtype='u')
    if var == 'v':
        v = mask_3d(read_netcdf(file_path, 'VVEL', time_index=time_index, t_start=t_start, t_end=t_end, time_average=time_average), grid, gtype='v')

    # Plot
    if var == 'temp':
        slice_plot(temp, grid, lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax, vmin=vmin, vmax=vmax, title=r'Temperature ($^{\circ}$C)', date_string=date_string, fig_name=fig_name)
    elif var == 'salt':
        slice_plot(salt, grid, lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax, vmin=vmin, vmax=vmax, title='Salinity (psu)', date_string=date_string, fig_name=fig_name)
    elif var == 'tminustf':
        slice_plot(t_minus_tf(temp, salt, grid), grid, lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax, vmin=vmin, vmax=vmax, ctype='plusminus', title=r'Difference from in-situ freezing point ($^{\circ}$C)', date_string=date_string, fig_name=fig_name)
    elif var == 'u':
        slice_plot(u, grid, gtype='u', lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax, vmin=vmin, vmax=vmax, ctype='plusminus', title='Zonal velocity (m/s)', date_string=date_string, fig_name=fig_name)
    elif var == 'v':
        slice_plot(v, grid, gtype='v', lon0=lon0, lat0=lat0, hmin=hmin, hmax=hmax, zmin=zmin, zmax=zmax, vmin=vmin, vmax=vmax, ctype='plusminus', title='Zonal velocity (m/s)', date_string=date_string, fig_name=fig_name)
    else:
        print 'Error (read_plot_slice): variable key ' + str(var) + ' does not exist'
        sys.exit()
        
    
