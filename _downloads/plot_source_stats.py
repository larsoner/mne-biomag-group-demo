"""
=====================
Source space clusters
=====================

Clustering in source space.
"""
from functools import partial
import os.path as op
import sys

import numpy as np
from scipy import stats

import mne
from mne import spatial_src_connectivity
from mne.stats import (spatio_temporal_cluster_1samp_test,
                       summarize_clusters_stc, ttest_1samp_no_p)

sys.path.append(op.join('..', '..', 'processing'))
from library.config import (meg_dir, subjects_dir, fsaverage_vertices,
                            exclude_subjects, N_JOBS)  # noqa: E402

faces = list()
scrambled = list()
for subject_id in range(1, 20):
    if subject_id in exclude_subjects:
        continue
    subject = "sub%03d" % subject_id
    print("processing subject: %s" % subject)
    data_path = op.join(meg_dir, subject)
    stc = mne.read_source_estimate(
        op.join(data_path, 'mne_dSPM_inverse_morph-faces_eq'))
    faces.append(stc.crop(0., None).magnitude().data.T)
    stc = mne.read_source_estimate(
        op.join(data_path, 'mne_dSPM_inverse_morph-scrambled_eq'))
    scrambled.append(stc.crop(0., None).magnitude().data.T)
    tstep = stc.tstep

###############################################################################
# Set up our contrast and initial p-value threshold

X = np.array(faces, float) - np.array(scrambled, float)
fsaverage_src = mne.read_source_spaces(
    op.join(subjects_dir, 'fsaverage', 'bem', 'fsaverage-5-src.fif'))
connectivity = spatial_src_connectivity(fsaverage_src)
# something like 0.01 is a more typical value here (or use TFCE!), but
# for speed here we'll use 0.001 (fewer clusters to handle)
p_threshold = 0.001
t_threshold = -stats.distributions.t.ppf(p_threshold / 2., len(X) - 1)

###############################################################################
# Here we could do an exact test with ``n_permutations=2**(len(X)-1)``,
# i.e. 32768 permutations, but this would take a long time. For speed and
# simplicity we'll do 1024.

stat_fun = partial(ttest_1samp_no_p, sigma=1e-3)
T_obs, clusters, cluster_p_values, H0 = clu = \
    spatio_temporal_cluster_1samp_test(
        X, connectivity=connectivity, n_jobs=N_JOBS, threshold=t_threshold,
        stat_fun=stat_fun, buffer_size=None, seed=0, verbose=True)

good_cluster_inds = np.where(cluster_p_values < 0.05)[0]
for ind in good_cluster_inds:
    print('Found cluster with p=%g' % (cluster_p_values[ind],))

###############################################################################
# Visualize the results:

stc_all_cluster_vis = summarize_clusters_stc(
    clu, tstep=tstep, vertices=fsaverage_vertices, subject='fsaverage')

brain = stc_all_cluster_vis.plot(
    hemi='both', subjects_dir=subjects_dir,
    time_label='Duration significant (ms)', views='ven',
    clim=dict(lims=[0, 0.1, 40], kind='value'), size=(1000, 1000))
brain.save_image(op.join('..', 'figures', 'source_stats.png'))
