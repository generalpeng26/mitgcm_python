#######################################################
# All things interpolation
#######################################################

import numpy as np
import sys

from utils import mask_land, mask_land_zice, mask_3d


# Interpolate from one grid type to another. Currently only u-grid to t-grid and v-grid to t-grid are supported.

# Arguments:
# data: array of dimension (maybe time) x (maybe depth) x lat x lon
# grid: Grid object
# gtype_in: grid type of "data". As in function Grid.get_lon_lat.
# gtype_out: grid type to interpolate to

# Optional keyword arguments:
# time_dependent: as in function apply_mask
# mask_shelf: indicates to mask the ice shelves as well as land. Only valid if "data" isn't depth-dependent.

# Output: array of the same dimension as "data", interpolated to the new grid type

def interp_grid (data, grid, gtype_in, gtype_out, time_dependent=False, mask_shelf=False):

    # Figure out if the field is depth-dependent
    if (time_dependent and len(data.shape)==4) or (not time dependent and len(data.shape)==3):
        depth_dependent=True
    else:
        depth_dependent=False
    # Make sure we're not trying to mask the ice shelf from a depth-dependent field
    if mask_shelf and depth_dependent:
        print "Error (interp_grid): can't set mask_shelf=True for a depth-dependent field."
        sys.exit()

    # Make sure the field is masked
    if depth_dependent:
        data = mask_3d(data, grid, gtype=gtype_in, time_dependent=time_dependent)
    else:
        if mask_shelf:
            data = mask_land_zice(data, grid, gtype=gtype_in, time_dependent=time_dependent)
        else:
            data = mask_land(data, grid, gtype=gtype_in, time_dependent=time_dependent)

    # Interpolate
    data_interp = np.ma.empty(data.shape)
    if gtype_in == 'u' and gtype_out == 't':
        # Midpoints in the x direction
        data_interp[...,:-1] = 0.5*(data[...,:-1] + data[...,1:])
        # Extend the easternmost column
        data_interp[...,-1] = data[...,-1]
    elif gtype_in == 'v' and gtype_out == 't':
        # Midpoints in the y direction
        data_interp[...,:-1,:] = 0.5*(data[...,:-1,:] + data[...,1:,:])
        # Extend the northernmost row
        data_interp[...,-1,:] = data[...,-1,:]
    else:
        print 'Error (interp_grid): interpolation from the ' + gtype_in + '-grid to the ' + gtype_out + '-grid is not yet supported'
        sys.exit()

    # Now apply the mask
    if depth_dependent:
        data_interp = mask_3d(data_interp, grid, gtype=gtype_out, time_dependent=time_dependent)
    else:
        if mask_shelf:
            data_interp = mask_land_zice(data_interp, grid, gtype=gtype_out, time_dependent=time_dependent)
        else:
            data_interp = mask_land(data_interp, grid, gtype=gtype_out, time_dependent=time_dependent)

    return data_interp
    

    
