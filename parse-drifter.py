import xarray, sys, datetime, math
from geopy import distance
from pymongo import MongoClient

client = MongoClient('mongodb://database/argo')
db = client.argo

def find_basin(lon, lat):
    # for a given lon, lat,
    # identify the basin from the lookup table.
    # choose the nearest non-nan grid point.

    gridspacing = 0.5
    basins = xarray.open_dataset('parameters/basinmask_01.nc')

    basin = basins['BASIN_TAG'].sel(LONGITUDE=lon, LATITUDE=lat, method="nearest").to_dict()['data']
    if math.isnan(basin):
        # nearest point was on land - find the nearest non nan instead.
        lonplus = math.ceil(lon / gridspacing)*gridspacing
        lonminus = math.floor(lon / gridspacing)*gridspacing
        latplus = math.ceil(lat / gridspacing)*gridspacing
        latminus = math.floor(lat / gridspacing)*gridspacing
        grids = [(basins['BASIN_TAG'].sel(LONGITUDE=lonminus, LATITUDE=latminus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latminus, lonminus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonminus, LATITUDE=latplus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latplus, lonminus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonplus, LATITUDE=latplus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latplus, lonplus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonplus, LATITUDE=latminus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latminus, lonplus)).miles)]

        grids = [x for x in grids if not math.isnan(x[0])]
        if len(grids) == 0:
            # all points on land
            #print('warning: all surrounding basin grid points are NaN')
            basin = -1
        else:
            grids.sort(key=lambda tup: tup[1])
            basin = grids[0][0]
    basins.close()
    return int(basin)

def parse_date(timestamp):
	# given an integer number of seconds since 1970-01-01T00:00:00Z <timestamp>,
	# return a corresponding datetime if possible, or None.

	t = None
	try:
		t = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
	except:
		pass

	return t

ds = xarray.open_dataset(sys.argv[1], decode_times=False)

# generate metadata object
meta = {
	"_id": ds.ID.data[0].decode("utf-8").strip(), 
	"rowsize": int(ds.rowsize.data[0]),
	"WMO": float(ds.WMO.data[0]),
	"expno": float(ds.expno.data[0]),
	"deploy_date": parse_date(int(ds.deploy_date.data[0])),
	"deploy_lon": float(ds.deploy_lon.data[0]),
	"deploy_lat": float(ds.deploy_lat.data[0]),
	"end_date": parse_date(int(ds.end_date.data[0])),
	"end_lon": float(ds.end_lon.data[0]),
	"end_lat": float(ds.end_lat.data[0]),
	"drogue_lost_date": parse_date(int(ds.drogue_lost_date.data[0])),
	"typedeath": float(ds.typedeath.data[0]),
	"typebuoy": ds.typebuoy.data[0].decode("utf-8").strip(),
	"source_url": 'https://www.aoml.noaa.gov/ftp/pub/phod/lumpkin/hourly/v2.00/netcdf/' + sys.argv[1].split('/')[-1]
}

try:
	db['drifterMeta'].insert_one(meta)
except BaseException as err:
	print('error: db write failure')
	print(err)
	print(meta)

# generate point data objects
for i in range(meta['rowsize']):
	point = {
		"_id": ds.ID.data[0].decode("utf-8").strip() + '_' + str(i),
		"geolocation": {
			"type": "Point",
			"coordinates": [float(ds.longitude.data[0][i]), float(ds.latitude.data[0][i])]
		},
		"basin": find_basin(float(ds.longitude.data[0][i]), float(ds.latitude.data[0][i])),
		"data_type": "drifter",
		"date_updated_argovis": datetime.datetime.now(),
		"source_info": [{
			"source": ["gdp"]
		}],
		"timestamp": parse_date(int(ds.time.data[0][i])),
		"data_keys": ["ve", "vn", "err_lon", "err_lat", "err_ve", "err_vn", "gap", "sst", "sst1", "sst2", "err_sst", "err_sst1", "err_sst2", "flg_sst", "flg_sst1", "flg_sst2"],
		"data": [[ds.ve.data[0][i], ds.vn.data[0][i], ds.err_lon.data[0][i], ds.err_lat.data[0][i], ds.err_ve.data[0][i], ds.err_vn.data[0][i], ds.err_vn.data[0][i], ds.gap.data[0][i], ds.sst.data[0][i], ds.sst.data[0][i], ds.sst1.data[0][i], ds.sst2.data[0][i],ds.err_sst.data[0][i], ds.err_sst1.data[0][i], ds.err_sst2.data[0][i], ds.flg_sst.data[0][i], ds.flg_sst1.data[0][i], ds.flg_sst2.data[0][i]]]
	}
	point['data'][0] = [float(x) for x in point['data'][0]]
	try:
		db['drifters'].insert_one(point)
	except BaseException as err:
		print('error: db write failure')
		print(err)
		print(point)








