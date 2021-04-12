import pandas as pd
import numpy as np
import math
from matplotlib import pyplot as plt
import imageio
import seaborn as sns
from shutil import rmtree
import os
from scipy.stats import ranksums
from statsmodels.stats.multitest import multipletests

class Node:
	def __init__(self,x ,y, name):
		self.x = x
		self.y = y
		self.name = name
		self.component = 0
		self.neighbors = []

	def __repr__(self):
		return "X: %d, Y: %d, spotID: %s, #NBs: %d" %(self.x, self.y, self.name, len(self.neighbors))

	def isNode(self, node):
		return (self.x == node.x and self.y == node.y)

	def contain_neighbor(self, node):
		if len(self.neighbors) == 0:
			return False
		for node1 in self.neighbors:
			if node1.isNode(node):
				return True
		return False

	def add_neighbor(self, node):
		if not self.contain_neighbor(node):
			self.neighbors.append(node)

	def assign_component(self, k):
		self.component=k


class CC:
	def __init__(self, nodes, name):
		self.nodes = nodes
		self.name = name
		self.size = len(nodes)

	def distance(self, node):
		dist = np.Inf
		for node2 in self.nodes:
			dist = min(dist, np.linalg.norm(np.array((node.x, node.y)) -
				np.array((node2.x, node2.y))))
		return dist

	def append(self, node):
		self.nodes.append(node)
		self.size += 1

def construct_graph(meta_data,radius=2):
	xs, ys = meta_data.iloc[:,0].tolist(), meta_data.iloc[:,1].tolist()
	spots = meta_data.index.tolist()
	nodes = []
	for i in range(len(xs)):
		nodes.append(Node(xs[i], ys[i], spots[i]))

	for node1 in nodes:
		for node2 in nodes:
			dist = np.linalg.norm(np.array((node1.x, node1.y)) -
				np.array((node2.x, node2.y)))
			if dist < radius:
				node1.add_neighbor(node2)
				node2.add_neighbor(node1)
	return nodes

def removeNodes(nodes, cnns):
	updated_nodes = []
	for i in range(len(nodes)):
		if nodes[i] not in cnns:
			updated_nodes.append(nodes[i])
	return updated_nodes

def spatialCCs(nodes, cor_mat, epi, merge=0):
	ccs = []
	while len(nodes) > 0:
		cnns = set([])
		node = nodes[0]
		cnns = DFS(cnns, nodes, node, cor_mat, epi)
		ccs.append(list(cnns))
		nodes = removeNodes(nodes, cnns)

	if merge > 0:
		k = 1
		small_nodes = []
		largeCCs = []
		for cc in ccs:
			if len(cc) <= merge:
				for node in cc:
					small_nodes.append(node)
			else:
				largeCCs.append(CC(cc, k))
				k += 1
		if len(largeCCs) == 0:
			return [small_nodes]
		merge_dict = {}
		for small_node in small_nodes:
			dist = np.Inf
			idx = 0
			for i in range(len(largeCCs)):
				if largeCCs[i].distance(small_node) < dist:
					dist = largeCCs[i].distance(small_node)
					idx = i
			#largeCCs[idx].append(small_node)
			merge_dict[small_node.name] = idx
		for small_node in small_nodes:
			largeCCs[merge_dict[small_node.name]].append(small_node)
		return [largeCC.nodes for largeCC in largeCCs]
	return ccs

def isValidNode(node, CNNs, cor_mat, epi):
	isValid = True
	for node2 in CNNs:
		if cor_mat.loc[node.name, node2.name] < epi:
			isValid = False
	return isValid

def DFS(CNNs, nodes, node, cor_mat, epi):
	if node not in CNNs:
		CNNs.add(node)
		for neighbor in node.neighbors:
			if (neighbor in nodes) and \
			(cor_mat.loc[neighbor.name, node.name] >= epi):
				DFS(CNNs, nodes, neighbor, cor_mat, epi)
	return CNNs

def plot_ccs(ccs, meta, title="none"):
	cc10, cc2, cc1 = 0, 0, 0
	xmin, xmax = meta.iloc[:, 0].min(), meta.iloc[:, 0].max()
	ymin, ymax = meta.iloc[:, 1].min(), meta.iloc[:, 1].max()
	colors = ["red", "orange", "yellow", "green",
				 "cyan", "blue", "purple", "gray",
				  "pink", "black"]
	df = meta.copy()
	# df['color'] = 'black'
	df["size"] = 1
	df.columns=['x','y', 'size']
	df['k'] = -1
	for i in range(len(ccs)):
		cc = ccs[i]
		for node in cc:
			x, y = node.x, node.y
			df.loc[(df.x == x) & (df.y==y),"size"] = len(cc)
			df.loc[(df.x == x) & (df.y==y),"k"] = i
	df = df.sort_values("size", ascending=False)
	df['cluster_name'] = df[['size','k']].apply(lambda x: "_".join(x.astype(str)), axis=1)
	unique_sizes = df["cluster_name"].drop_duplicates().tolist()
	cluster_dict = dict(zip(unique_sizes, 
		range(len(unique_sizes))))
	clusters = []
	for s in df["cluster_name"].tolist():
		i = cluster_dict[s]
		if i > len(colors) - 1:
			clusters.append("lightgray")
		else:
			clusters.append(colors[i])
	df['cluster'] = clusters
	return df

# input count matrix should be log scaled
def detectSDEs(fn, ep, log=False):
	count, meta = read_ST_data(fn)

	if log:
		count_filt = np.log2(count + 1)
	else:
		count_filt = count.copy()
	cor_mat = spot_PCA_sims(count_filt)

	nodes = construct_graph(meta)
	ccs = spatialCCs(nodes, cor_mat, ep, merge=0)

	genes = count_filt.columns.tolist()
	cc_dfs = []
	for i in range(len(ccs)):
		cc = ccs[i]
		if len(cc) >= 5:
			cc_spots= [c.name for c in cc]
			count_cc = count_filt.loc[cc_spots, genes]
			other_spots = [s for s in count_filt.index.tolist() if s not in cc_spots]
			count_other = count_filt.loc[other_spots, genes]
			pvals, logFCs = [], []
			for g in genes:
				pval = ranksums(count_cc.loc[:,g].to_numpy(), count_other.loc[:, g].to_numpy())[1]
				logFC = np.mean(count_cc.loc[:,g].to_numpy()) - np.mean(count_other.loc[:, g].to_numpy())
				pvals.append(pval)
				logFCs.append(logFC)
			cc_df = pd.DataFrame({"gene":genes, "pval": pvals, "logFC":logFCs})
			cc_df["padj"] = multipletests(cc_df.pval.to_numpy())[1]
			cc_df=cc_df.loc[cc_df.padj <= 0.05,:]
			cc_df["component"] = i
			cc_dfs.append(cc_df)
	cc_dfs = pd.concat(cc_dfs)
	print(cc_dfs)
	return cc_dfs