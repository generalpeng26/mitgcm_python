#######################################################
# Everything to do with reading the grid
# You can build this using binary grid files or NetCDF output files created by xmitgcm which include all the necessary grid variables.
#
# For binary, put the *.data and *.meta files for the following variables into one directory: Depth, DRC, DRF, DXG, DYG, hFacC, hFacS, hFacW, RAC, RC, RF, XC, XG, YC, YG.
#
# IMPORTANT NOTE: The calculation of ice shelf draft and bathymetry may not be accurate in partial cells which include both ice and seafloor (i.e. the wet portion of the cell is in the middle, not at the top or bottom). However, this should never happen in domains created using make_domain.py, as the digging ensures all water columns are at least two (possibly partial) cells deep.
#######################################################

import numpy as np
import sys
import os

from file_io import read_netcdf
from utils import fix_lon_range, real_dir, split_longitude
from constants import fris_bounds, ewed_bounds, sose_res, sws_shelf_bounds


# Grid object containing lots of grid variables:
# nx, ny, nz: dimensions of grid
# lon_2d: longitude at cell centres (degrees, XY)
# lat_2d: latitude at cell centres (degrees, XY)
# lon_corners_2d: longitude at cell corners (degrees, XY)
# lat_corners_2d: latitude at cell corners (degrees, XY)
# lon_1d, lat_1d, lon_corners_1d, lat_corners_1d: 1D versions of the corresponding 2D arrays, note this assumes a polar spherical grid! (X or Y)
# dx_s: width of southern cell edge (m, XY)
# dy_w: height of western cell edge (m, XY)
# dA: area of cell (m^2, XY)
# z: depth axis at cell centres (negative, m, Z)
# z_edges: depth axis at cell interfaces; dimension 1 larger than z (negative, m, Z)
# dz: thickness of cell (m, Z)
# dz_t: thickness between cell centres (m, Z)
# hfac: partial cell fraction (XYZ)
# hfac_w: partial cell fraction at u-points (XYZ)
# hfac_s: partial cell fraction at v-points (XYZ)
# bathy: bathymetry (negative, m, XY)
# draft: ice shelf draft (negative, m, XY)
# wct: water column thickness (m, XYZ)
# land_mask, land_mask_u, land_mask_v: boolean land masks on the tracer, u, and v grids (XY). True means it is masked.
# ice_mask, ice_mask_u, ice_mask_v: boolean ice shelf masks on the tracer, u, and v grids (XY)
# fris_mask, fris_mask_u, fris_mask_v: boolean FRIS masks on the tracer, u, and v grids (XY)
# ewed_mask: boolean Eastern Weddell ice shelf mask on the tracer grid (XY)
# sws_shelf_mask: boolean Southern Weddell Sea continental shelf mask on the tracer grid (XY)
class Grid:

    # Initialisation arguments:
    # file_path: path to NetCDF grid file OR directory containing binary files
    # x_is_lon: indicates that X indicates longitude. If True, max_lon will be enforced.
    # max_lon: will adjust longitude to be in the range (max_lon-360, max_lon). By default the code will work out whether (0, 360) or (-180, 180) is more appropriate.
    def __init__ (self, path, x_is_lon=True, max_lon=None):

        if path.endswith('.nc'):
            use_netcdf=True
        elif os.path.isdir(path):
            use_netcdf=False
            path = real_dir(path)
            from MITgcmutils import rdmds
        else:
            print 'Error (Grid): ' + path + ' is neither a NetCDF file nor a directory'
            sys.exit()
            
        # Read variables
        # Note that some variables are capitalised differently in NetCDF versus binary, so can't make this more efficient...
        if use_netcdf:
            self.lon_2d = read_netcdf(path, 'XC')
            self.lat_2d = read_netcdf(path, 'YC')
            self.lon_corners_2d = read_netcdf(path, 'XG')
            self.lat_corners_2d = read_netcdf(path, 'YG')
            self.dx_s = read_netcdf(path, 'dxG')
            self.dy_w = read_netcdf(path, 'dyG')
            self.dA = read_netcdf(path, 'rA')
            self.z = read_netcdf(path, 'Z')
            self.z_edges = read_netcdf(path, 'Zp1')
            self.dz = read_netcdf(path, 'drF')
            self.dz_t = read_netcdf(path, 'drC')
            self.hfac = read_netcdf(path, 'hFacC')
            self.hfac_w = read_netcdf(path, 'hFacW')
            self.hfac_s = read_netcdf(path, 'hFacS')
            self.wct = read_netcdf(path, 'Depth')
        else:
            self.lon_2d = rdmds(path+'XC')
            self.lat_2d = rdmds(path+'YC')
            self.lon_corners_2d = rdmds(path+'XG')
            self.lat_corners_2d = rdmds(path+'YG')
            self.dx_s = rdmds(path+'DXG')
            self.dy_w = rdmds(path+'DYG')
            self.dA = rdmds(path+'RAC')
            # Remove singleton dimensions from 1D depth variables
            self.z = rdmds(path+'RC').squeeze()
            self.z_edges = rdmds(path+'RF').squeeze()
            self.dz = rdmds(path+'DRF').squeeze()
            self.dz_t = rdmds(path+'DRC').squeeze()
            self.hfac = rdmds(path+'hFacC')
            self.hfac_w = rdmds(path+'hFacW')
            self.hfac_s = rdmds(path+'hFacS')
            self.wct = rdmds(path+'Depth')

        # Make 1D versions of latitude and longitude arrays (only useful for regular lat-lon grids)
        if len(self.lon_2d.shape) == 2:
            self.lon_1d = self.lon_2d[0,:]
            self.lat_1d = self.lat_2d[:,0]
            self.lon_corners_1d = self.lon_corners_2d[0,:]
            self.lat_corners_1d = self.lat_corners_2d[:,0]
        elif len(self.lon_2d.shape) == 1:
            # xmitgcm output has these variables as 1D already. So make 2D ones.
            self.lon_1d = np.copy(self.lon_2d)
            self.lat_1d = np.copy(self.lat_2d)
            self.lon_corners_1d = np.copy(self.lon_corners_2d)
            self.lat_corners_1d = np.copy(self.lat_corners_2d)
            self.lon_2d, self.lat_2d = np.meshgrid(self.lon_1d, self.lat_1d)
            self.lon_corners_2d, self.lat_corners_2d = np.meshgrid(self.lon_corners_1d, self.lat_corners_1d)

        # Decide on longitude range
        if max_lon is None and x_is_lon:            
            # Choose range automatically
            if np.amin(self.lon_1d) < 180 and np.amax(self.lon_1d) > 180:
                # Domain crosses 180E, so use the range (0, 360)
                max_lon = 360
            else:
                # Use the range (-180, 180)
                max_lon = 180
            # Do one array to test
            self.lon_1d = fix_lon_range(self.lon_1d, max_lon=max_lon)
            # Make sure it's strictly increasing now
            if not np.all(np.diff(self.lon_1d)>0):
                print 'Error (Grid): Longitude is not strictly increasing either in the range (0, 360) or (-180, 180).'
                sys.exit()
        self.lon_1d = fix_lon_range(self.lon_1d, max_lon=max_lon)
        self.lon_corners_1d = fix_lon_range(self.lon_corners_1d, max_lon=max_lon)
        self.lon_2d = fix_lon_range(self.lon_2d, max_lon=max_lon)
        self.lon_corners_2d = fix_lon_range(self.lon_corners_2d, max_lon=max_lon)

        # Save dimensions
        self.nx = self.lon_1d.size
        self.ny = self.lat_1d.size
        self.nz = self.z.size

        # Calculate ice shelf draft
        self.draft = np.zeros([self.ny, self.nx])
        self.draft[:,:] = np.nan
        # Loop from top to bottom
        for k in range(self.nz):
            hfac_tmp = self.hfac[k,:]
            # Identify wet cells with no draft assigned yet
            index = (hfac_tmp!=0)*np.isnan(self.draft)
            self.draft[index] = self.z_edges[k] - self.dz[k]*(1-hfac_tmp[index])
        # Anything still NaN is land mask and should have zero draft
        index = np.isnan(self.draft)
        self.draft[index] = 0

        # Calculate bathymetry
        self.bathy = self.draft - self.wct

        # Create masks on the t, u, and v grids
        # Land masks
        self.land_mask = self.build_land_mask(self.hfac)
        self.land_mask_u = self.build_land_mask(self.hfac_w)
        self.land_mask_v = self.build_land_mask(self.hfac_s)
        # Ice shelf masks
        self.ice_mask = self.build_ice_mask(self.hfac)
        self.ice_mask_u = self.build_ice_mask(self.hfac_w)
        self.ice_mask_v = self.build_ice_mask(self.hfac_s)
        # FRIS masks
        self.fris_mask = self.build_fris_mask(self.ice_mask, self.lon_2d, self.lat_2d)
        self.fris_mask_u = self.build_fris_mask(self.ice_mask_u, self.lon_corners_2d, self.lat_2d)
        self.fris_mask_v = self.build_fris_mask(self.ice_mask_v, self.lon_2d, self.lat_corners_2d)
        # Eastern Weddell ice shelf mask
        self.ewed_mask = self.build_ewed_mask(self.ice_mask, self.lon_2d, self.lat_2d)
        # Southern Weddell Sea continental shelf mask
        self.sws_shelf_mask = self.build_sws_shelf_mask(self.land_mask, self.ice_mask, self.lon_2d, self.lat_2d, self.bathy)

        
    # Given a 3D hfac array on any grid, create the land mask.
    def build_land_mask (self, hfac):

        return np.sum(hfac, axis=0)==0


    # Given a 3D hfac array on any grid, create the ice shelf mask.
    def build_ice_mask (self, hfac):

        return (np.sum(hfac, axis=0)!=0)*(hfac[0,:]<1)


    # Create a mask just containing FRIS ice shelf points.
    # Arguments:
    # ice_mask, lon, lat: 2D arrays of the ice shelf mask, longitude, and latitude on any grid
    def build_fris_mask (self, ice_mask, lon, lat):

        fris_mask = np.zeros(ice_mask.shape, dtype='bool')
        # Identify FRIS in two parts, split along the line 45W
        # Each set of 4 bounds is in form [lon_min, lon_max, lat_min, lat_max]
        regions = [[fris_bounds[0], -45, fris_bounds[2], -74.7], [-45, fris_bounds[1], fris_bounds[2], -77.85]]
        for bounds in regions:
            # Select the ice shelf points within these bounds
            index = ice_mask*(lon >= bounds[0])*(lon <= bounds[1])*(lat >= bounds[2])*(lat <= bounds[3])
            fris_mask[index] = True
        return fris_mask

    
    # Like build_fris_mask, but for Eastern Weddell ice shelves. A fair bit simpler.
    def build_ewed_mask (self, ice_mask, lon, lat):

        return ice_mask*(lon >= ewed_bounds[0])*(lon <= ewed_bounds[1])*(lat >= ewed_bounds[2])*(lat <= ewed_bounds[3])


    # Create a mask just containing continental shelf points in front of FRIS.
    # These points must be:
    # 1. within the rectangle given by sws_shelf_bounds,
    # 2. bathymetry shallower than 1250 m,
    # 3. not ice shelf or land points.
    def build_sws_shelf_mask(self, land_mask, ice_mask, lon, lat, bathy):

        return np.invert(land_mask)*np.invert(ice_mask)*(bathy >= -1250)*(lon >= sws_shelf_bounds[0])*(lon <= sws_shelf_bounds[1])*(lat >= sws_shelf_bounds[2])*(lat <= sws_shelf_bounds[3])

        
    # Return the longitude and latitude arrays for the given grid type.
    # 't' (default), 'u', 'v', 'psi', and 'w' are all supported.
    # Default returns the 2D meshed arrays; can set dim=1 to get 1D axes.
    def get_lon_lat (self, gtype='t', dim=2):

        if dim == 1:
            lon = self.lon_1d
            lon_corners = self.lon_corners_1d
            lat = self.lat_1d
            lat_corners = self.lat_corners_1d
        elif dim == 2:
            lon = self.lon_2d
            lon_corners = self.lon_corners_2d
            lat = self.lat_2d
            lat_corners = self.lat_corners_2d
        else:
            print 'Error (get_lon_lat): dim must be 1 or 2'
            sys.exit()

        if gtype in ['t', 'w']:
            return lon, lat
        elif gtype == 'u':
            return lon_corners, lat
        elif gtype == 'v':
            return lon, lat_corners
        elif gtype == 'psi':
            return lon_corners, lat_corners
        else:
            print 'Error (get_lon_lat): invalid gtype ' + gtype
            sys.exit()


    # Return the hfac array for the given grid type.
    # 'psi' and 'w' have no hfac arrays so they are not supported
    def get_hfac (self, gtype='t'):

        if gtype == 't':
            return self.hfac
        elif gtype == 'u':
            return self.hfac_w
        elif gtype == 'v':
            return self.hfac_s
        else:
            print 'Error (get_hfac): no hfac exists for the ' + gtype + ' grid'
            sys.exit()


    # Return the land mask for the given grid type.
    def get_land_mask (self, gtype='t'):

        if gtype == 't':
            return self.land_mask
        elif gtype == 'u':
            return self.land_mask_u
        elif gtype == 'v':
            return self.land_mask_v
        else:
            print 'Error (get_land_mask): no mask exists for the ' + gtype + ' grid'
            sys.exit()

            
    # Return the ice shelf mask for the given grid type.
    def get_ice_mask (self, gtype='t'):

        if gtype == 't':
            return self.ice_mask
        elif gtype == 'u':
            return self.ice_mask_u
        elif gtype == 'v':
            return self.ice_mask_v
        else:
            print 'Error (get_ice_mask): no mask exists for the ' + gtype + ' grid'
            sys.exit()


    # Return the FRIS mask for the given grid type.
    def get_fris_mask (self, gtype='t'):

        if gtype == 't':
            return self.fris_mask
        elif gtype == 'u':
            return self.fris_mask_u
        elif gtype == 'v':
            return self.fris_mask_v
        else:
            print 'Error (get_fris_mask): no mask exists for the ' + gtype + ' grid'
            sys.exit()


# Interface to Grid for situations such as read_plot_latlon where there are three possibilities:
# (1) the Grid object is precomputed and saved in variable "grid"; nothing to do
# (2) the Grid object is not precomputed, but file_path (where the model output is being read from in the master function) contains the grid variables; build the Grid from this file
# (3) the Grid object is not precomputed and file_path does not contain the grid variables; "grid" instead contains the path to either (a) the binary grid directory or (b) a NetCDF file containing the grid variables; build the grid from this path
def choose_grid (grid, file_path):

    if grid is None:
        # Build the grid from file_path (option 2 above)
        grid = Grid(file_path)
    else:
        if not isinstance(grid, Grid):
            # Create a Grid object from the given path (option 3 above)
            grid = Grid(grid)
        # Otherwise, the Grid object was precomputed (option 1 above)
    return grid


# Interface to Grid for situations such as sose_ics, where max_lon should be set so there is no jump in longitude in the middle of the model domain. Create the Grid object from grid_path and make sure the user has chosen the correct value for split (180 or 0).
def grid_check_split (grid_path, split):

    if split == 180:
        grid = Grid(grid_path, max_lon=180)
        if grid.lon_1d[0] > grid.lon_1d[-1]:
            print 'Error (grid_check_split): Looks like your domain crosses 180E. Run this again with split=0.'
            sys.exit()
    elif split == 0:
        grid = Grid(grid_path, max_lon=360)
        if grid.lon_1d[0] > grid.lon_1d[-1]:
            print 'Error (grid_check_split): Looks like your domain crosses 0E. Run this again with split=180.'
            sys.exit()
    else:
        print 'Error (grid_check_split): split must be 180 or 0'
        sys.exit()
    return grid


# Special class for the SOSE grid, which is read from a few binary files. It inherits many functions from Grid.

# To speed up interpolation, trim and/or extend the SOSE grid to agree with the bounds of model_grid (Grid object for the model which you'll be interpolating SOSE data to).
# Depending on the longitude range within the model grid, it might also be necessary to rearrange the SOSE grid so it splits at 180E=180W (split=180, implying longitude ranges from -180 to 180 and max_lon=180 when creating model_grid) instead of its native split at 0E (split=0, implying longitude ranges from 0 to 360 and max_lon=360 when creating model_grid).
# The rule of thumb is, if your model grid includes 0E, split at 180E, and vice versa. A circumpolar model should be fine either way as long as it doesn't have any points in the SOSE periodic boundary gap (in which case you'll have to write a patch). 
# MOST IMPORTANTLY, if you are reading a SOSE binary file, don't use rdmds. Use the class function read_field (defined below) which will repeat the trimming/extending/splitting/rearranging correctly.

# If you don't want to do any trimming or extending, just set model_grid=None.
class SOSEGrid(Grid):

    def __init__ (self, grid_dir, model_grid=None, split=0):

        from MITgcmutils import rdmds

        self.trim_extend = True
        if model_grid is None:
            self.trim_extend = False

        if self.trim_extend:
            # Error checking for which longitude range we're in
            if split == 180:
                max_lon = 180
                if np.amax(model_grid.lon_2d) > max_lon:
                    print 'Error (SOSEGrid): split=180 does not match model grid'
            elif split == 0:
                max_lon = 360
                if np.amin(model_grid.lon_2d) < 0:
                    print 'Error (SOSEGrid): split=0 does not match model grid'
            else:
                print 'Error (SOSEGrid): split must be 180 or 0'
                sys.exit()
        else:
            max_lon = 360        

        grid_dir = real_dir(grid_dir)        

        # Read longitude at cell centres (make the 2D grid 1D as it's regular)
        self.lon_1d = fix_lon_range(rdmds(grid_dir+'XC'), max_lon=max_lon)[0,:]
        if split == 180:
            # Split the domain at 180E=180W and rearrange the two halves so longitude is strictly ascending
            self.i_split = np.nonzero(self.lon_1d < 0)[0][0]
            self.lon_1d = split_longitude(self.lon_1d, self.i_split)
        else:
            # Set i_split to 0 which won't actually do anything
            self.i_split = 0
            
        # Read longitude at cell corners, splitting as before
        self.lon_corners_1d = split_longitude(fix_lon_range(rdmds(grid_dir+'XG'), max_lon=max_lon), self.i_split)[0,:]
        if self.lon_corners_1d[0] > 0:
            # The split happened between lon_corners[i_split] and lon[i_split].
            # Take mod 360 on this index of lon_corners to make sure it's strictly increasing.
            self.lon_corners_1d[0] -= 360

        # Make sure the longitude axes are strictly increasing after the splitting
        if not np.all(np.diff(self.lon_1d)>0) or not np.all(np.diff(self.lon_corners_1d)>0):
            print 'Error (SOSEGrid): longitude is not strictly increasing'
            sys.exit()
            
        # Read latitude at cell centres and corners
        self.lat_1d = rdmds(grid_dir+'YC')[:,0]
        self.lat_corners_1d = rdmds(grid_dir+'YG')[:,0]
        # Read depth
        self.z = rdmds(grid_dir+'RC').squeeze()

        # Save original dimensions
        sose_nx = self.lon_1d.size
        sose_ny = self.lat_1d.size
        sose_nz = self.z.size

        if self.trim_extend:
        
            # Trim and/or extend the axes
            # Notes about this:
            # Longitude can only be trimmed as SOSE considers all longitudes (someone doing a high-resolution circumpolar model with points in the gap might need to write a patch to wrap the SOSE grid around)
            # Latitude can be trimmed in both directions, or extended to the south (not extended to the north - if you need to do this, SOSE is not the right product for you!)
            # Depth can be extended by one level in both directions, and the deeper bound can also be trimmed
            # The indices i, j, and k will be kept track of with 4 variables each. For example, with longitude:
            # i0_before = first index we care about
            #           = how many cells to trim at beginning
            # i0_after = i0_before's position in the new grid
            #          = how many cells to extend at beginning
            # i1_before = first index we don't care about
            #           sose_nx - i1_before = how many cells to trim at end
            # i1_after = i1_before's position in the new grid
            #          = i1_before - i0_before + i0_after
            # nx = length of new grid
            #      nx - i1_after = how many cells to extend at end

            # Find bounds on model grid
            xmin = np.amin(model_grid.lon_corners_2d)
            xmax = np.amax(model_grid.lon_2d)
            ymin = np.amin(model_grid.lat_corners_2d)
            ymax = np.amax(model_grid.lat_2d)
            z_shallow = model_grid.z[0]
            z_deep = model_grid.z[-1]

            # Western bound (use longitude at cell centres to make sure all grid types clear the bound)
            if xmin == self.lon_1d[0]:
                # Nothing to do
                self.i0_before = 0            
            elif xmin > self.lon_1d[0]:
                # Trim
                self.i0_before = np.nonzero(self.lon_1d > xmin)[0][0] - 1
            else:
                print 'Error (SOSEGrid): not allowed to extend westward'
                sys.exit()
            self.i0_after = 0

            # Eastern bound (use longitude at cell corners, i.e. western edge)
            if xmax == self.lon_corners_1d[-1]:
                # Nothing to do
                self.i1_before = sose_nx
            elif xmax < self.lon_corners_1d[-1]:
                # Trim
                self.i1_before = np.nonzero(self.lon_corners_1d > xmax)[0][0] + 1
            else:
                print 'Error (SOSEGrid): not allowed to extend eastward'
                sys.exit()
            self.i1_after = self.i1_before - self.i0_before + self.i0_after
            self.nx = self.i1_after

            # Southern bound (use latitude at cell centres)
            if ymin == self.lat_1d[0]:
                # Nothing to do
                self.j0_before = 0
                self.j0_after = 0
            elif ymin > self.lat_1d[0]:
                # Trim
                self.j0_before = np.nonzero(self.lat_1d > ymin)[0][0] - 1
                self.j0_after = 0
            elif ymin < self.lat_1d[0]:
                # Extend
                self.j0_after = int(np.ceil((self.lat_1d[0]-ymin)/sose_res))
                self.j0_before = 0

            # Northern bound (use latitude at cell corners, i.e. southern edge)
            if ymax == self.lat_corners_1d[-1]:
                # Nothing to do
                self.j1_before = sose_ny
            elif ymax < self.lat_corners_1d[-1]:
                # Trim
                self.j1_before = np.nonzero(self.lat_corners_1d > ymax)[0][0] + 1
            else:
                print 'Error (SOSEGrid): not allowed to extend northward'
                sys.exit()
            self.j1_after = self.j1_before - self.j0_before + self.j0_after
            self.ny = self.j1_after

            # Depth
            self.k0_before = 0
            if z_shallow <= self.z[0]:
                # Nothing to do
                self.k0_after = 0
            else:
                # Extend
                self.k0_after = 1
            if z_deep > self.z[-1]:
                # Trim
                self.k1_before = np.nonzero(self.z < z_deep)[0][0] + 1
            else:
                # Either extend or do nothing
                self.k1_before = sose_nz
            self.k1_after = self.k1_before + self.k0_after
            if z_deep < self.z[-1]:
                # Extend
                self.nz = self.k1_after + 1
            else:
                self.nz = self.k1_after

            # Now we have the indices we need, so trim/extend the axes as needed
            # Longitude: can only trim
            self.lon_1d = self.lon_1d[self.i0_before:self.i1_before]
            self.lon_corners_1d = self.lon_corners_1d[self.i0_before:self.i1_before]
            # Latitude: can extend on south side, trim on both sides
            lat_extend = np.flipud(-1*(np.arange(self.j0_after)+1)*sose_res + self.lat_1d[self.j0_before])
            lat_trim = self.lat_1d[self.j0_before:self.j1_before]        
            self.lat_1d = np.concatenate((lat_extend, lat_trim))
            lat_corners_extend = np.flipud(-1*(np.arange(self.j0_after)+1)*sose_res + self.lat_corners_1d[self.j0_before])
            lat_corners_trim = self.lat_corners_1d[self.j0_before:self.j1_before]        
            self.lat_corners_1d = np.concatenate((lat_corners_extend, lat_corners_trim))
            # Depth: can extend on both sides (depth 0 at top and extrapolated at bottom to clear the deepest model depth), trim on deep side
            z_above = 0*np.ones([self.k0_after])  # Will either be [0] or empty
            z_middle = self.z[self.k0_before:self.k1_before]
            z_below = (2*model_grid.z[-1] - model_grid.z[-2])*np.ones([self.nz-self.k1_after])   # Will either be [something deeper than z_deep] or empty
            self.z = np.concatenate((z_above, z_middle, z_below))

            # Make sure we cleared those bounds
            if self.lon_corners_1d[0] > xmin:
                print 'Error (SOSEGrid): western bound not cleared'
                sys.exit()
            if self.lon_corners_1d[-1] < xmax:
                print 'Error (SOSEGrid): eastern bound not cleared'
                sys.exit()
            if self.lat_corners_1d[0] > ymin:
                print 'Error (SOSEGrid): southern bound not cleared'
                sys.exit()
            if self.lat_corners_1d[-1] < ymax:
                print 'Error (SOSEGrid): northern bound not cleared'
                sys.exit()
            if self.z[0] < z_shallow:
                print 'Error (SOSEGrid): shallow bound not cleared'
                sys.exit()
            if self.z[-1] > z_deep:
                print 'Error (SOSEGrid): deep bound not cleared'
                sys.exit()

            # Now read the rest of the variables we need, splitting/trimming/extending them as needed
            self.hfac = self.read_field(grid_dir+'hFacC', 'xyz', fill_value=0)
            self.hfac_w = self.read_field(grid_dir+'hFacW', 'xyz', fill_value=0)
            self.hfac_s = self.read_field(grid_dir+'hFacS', 'xyz', fill_value=0)

        else:

            # Nothing fancy to do, so read the rest of the fields
            self.hfac = rdmds(grid_dir+'hFacC')
            self.hfac_w = rdmds(grid_dir+'hFacW')
            self.hfac_s = rdmds(grid_dir+'hFacS')
            self.nx = sose_nx
            self.ny = sose_ny
            self.nz = sose_nz

        # Create land masks
        self.land_mask = self.build_land_mask(self.hfac)
        self.land_mask_u = self.build_land_mask(self.hfac_w)
        self.land_mask_v = self.build_land_mask(self.hfac_s)
    


    # Read a field from a binary MDS file and split, trim, extend as needed.
    # The filename can include the suffix .data or not, it doesn't matter.
    # The field can be time dependent: dimensions must be one of 'xy', 'xyt', 'xyz', or 'xyzt'.
    # Extended regions will just be filled with fill_value for now. See function discard_and_fill in interpolation.py for how to extrapolate data into these regions.
    def read_field (self, file_path, dimensions, fill_value=-9999):

        from MITgcmutils import rdmds
        
        if self.trim_extend:

            # Read the field and split along longitude
            data_orig = split_longitude(rdmds(file_path.replace('.data', '')), self.i_split)
            # Create a new array of the correct dimension (including extended regions)
            data_shape = [self.ny, self.nx]
            if 'z' in dimensions:
                data_shape = [self.nz] + data_shape        
            if 't' in dimensions:
                num_time = data_orig.shape[0]
                data_shape = [num_time] + data_shape
            data = np.zeros(data_shape) + fill_value

            # Trim
            if 'z' in dimensions:
                data[..., self.k0_after:self.k1_after, self.j0_after:self.j1_after, self.i0_after:self.i1_after] = data_orig[..., self.k0_before:self.k1_before, self.j0_before:self.j1_before, self.i0_before:self.i1_before]
            else:
                data[..., self.j0_after:self.j1_after, self.i0_after:self.i1_after] = data_orig[..., self.j0_before:self.j1_before, self.i0_before:self.i1_before]

        else:
            # Nothing fancy to do
            data = rdmds(file_path.replace('.data', ''))

        return data
            

    # Return the longitude and latitude arrays for the given grid type.
    def get_lon_lat (self, gtype='t', dim=1):

        # We need to have dim as a keyword argument so this agrees with the Grid class function, but there is no option for dim=2
        if dim != 1:
            print 'Error (get_lon_lat): must have dim=1 for SOSE grid'
            sys.exit()

        if gtype in ['t', 'w']:
            return self.lon_1d, self.lat_1d
        elif gtype == 'u':
            return self.lon_corners_1d, self.lat_1d
        elif gtype == 'v':
            return self.lon_1d, self.lat_corners_1d
        elif gtype == 'psi':
            return self.lon_corners_1d, self.lat_corners_1d
        else:
            print 'Error (get_lon_lat): invalid gtype ' + gtype
            sys.exit()


    # Dummy definitions for functions we don't want, which would otherwise be inhertied from Grid
    def build_ice_mask (self, hfac):
        print 'Error (SOSEGrid): no ice shelves to mask'
        sys.exit()
    def build_fris_mask (self, hfac):
        print 'Error (SOSEGrid): no ice shelves to mask'
        sys.exit()
    def get_ice_mask (self, gtype='t'):
        print 'Error (SOSEGrid): no ice shelves to mask'
        sys.exit()
    def get_fris_mask (self, gtype='t'):
        print 'Error (SOSEGrid): no ice shelves to mask'
        sys.exit()



