from imputers import *
import os
import sys
#from Data import Data
from time import time
import Data
sys.path.append("../src/")
import utils

if __name__ == '__main__':
	folder = sys.argv[1]
	norm = "cpm"
	ep = 0.7
	merge = 0
	radius = 2

	if "slideseq" in folder:
		merge = 50
		radius = 100

	for i in range(5):
		fn = os.path.join(folder, "ho_data_%d.csv" %i)
		data = Data.Data(countpath=fn, radius=radius, merge=merge)
		# for imputer_name in ["MAGIC", "knnSmooth", "mcImpute", "spKNN", "spImpute"]:
		for imputer_name in ["spImpute"]:
#		for imputer_name in ["MAGIC", "knnSmooth","spKNN"]:
			norm_outF = os.path.join(folder, "%s_%d.csv" %(imputer_name, i))
			#raw_outF = os.path.join(folder, "%s_raw_%d.csv" %(imputer_name, i))
			#libsizeF = os.path.join(folder, "libsize.csv")
			st_time = time()
			imputer = Imputer(imputer_name, data)

			imputed_data = imputer.fit_transform()
			#imputed_raw = utils.data_denorm(imputed_data, libsizeF, norm)

			imputed_data.to_csv(norm_outF)
			#imputed_raw.to_csv(raw_outF)

			print("[%d, %s] elapsed %.1f seconds.." %(i, imputer_name, time() - st_time))

	# fn = os.path.join(folder, "ho_data_0.csv")
	# data = Data.Data(countpath=fn, radius=radius, merge=merge)
	# for ep in [0,0.2,0.4,0.6,0.8]:
	# 	st_time = time()
	# 	imputer_name = "spImpute"
	# 	out_fn = os.path.join(folder, "spImpute_%d.csv" %(ep*100))
	# 	data.update_ep(ep)
	# 	imputer = Imputer(imputer_name, data)
	# 	imputed_data = imputer.fit_transform()
	# 	imputed_data.to_csv(out_fn)
	# 	print("[%.2f, %s] elapsed %.1f seconds.." %(ep, imputer_name, time() - st_time))

