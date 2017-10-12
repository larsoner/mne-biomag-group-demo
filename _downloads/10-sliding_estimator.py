"""
=================
Sliding estimator
=================

A sliding estimator fits a logistic legression model for every time point.
In this example, we contrast the condition 'famous' against 'scrambled'
using this approach. The end result is an averaging effect across sensors.
The contrast across different sensors are combined into a single plot.

Results script: :ref:`sphx_glr_auto_examples_statistics_plot_sliding_estimator.py`
"""  # noqa: E501

###############################################################################
# Let us first import the libraries

import os

import numpy as np
from scipy.io import savemat

import mne
from mne.decoding import SlidingEstimator, cross_val_multiscore
from mne.selection import read_selection

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression

from library.config import meg_dir, l_freq, N_JOBS

###############################################################################
# Then we write a function to do time decoding on one subject


def run_time_decoding(subject_id, condition1, condition2):
    print("processing subject: %s (%s vs %s)"
          % (subject_id, condition1, condition2))

    subject = "sub%03d" % subject_id
    data_path = os.path.join(meg_dir, subject)
    epochs = mne.read_epochs(os.path.join(data_path,
                             '%s_highpass-%sHz-epo.fif' % (subject, l_freq)))

    # We define the epochs and the labels
    n_cond1 = len(epochs[condition1])
    n_cond2 = len(epochs[condition2])
    y = np.r_[np.ones(n_cond1), np.zeros(n_cond2)]
    epochs = mne.concatenate_epochs([epochs[condition1],
                                    epochs[condition2]])

    # Let us restrict ourselves to the occipital channels
    ch_names = [ch_name.replace(' ', '') for ch_name
                in read_selection('occipital')]
    epochs.pick_types(meg='mag').pick_channels(ch_names)

    # Use AUC because chance level is same regardless of the class balance
    scores = cross_val_multiscore(
        SlidingEstimator(make_pipeline(StandardScaler(), LogisticRegression()),
                         scoring='roc_auc', n_jobs=N_JOBS),
        X=epochs.get_data(), y=y, cv=StratifiedKFold(n_splits=10))

    # let's save the scores now
    a_vs_b = '%s_vs_%s' % (os.path.basename(condition1),
                           os.path.basename(condition2))
    fname_td = os.path.join(data_path, '%s-td-auc-%s.mat'
                            % (subject, a_vs_b))
    savemat(fname_td, {'scores': scores, 'times': epochs.times})


# Here we go parallel inside the :class:`mne.decoding.SlidingEstimator`
# so we don't dispatch manually to multiple jobs.

for subject_id in range(1, 20):
    for conditions in (('face', 'scrambled'),
                       ('face/famous', 'face/unfamiliar')):
        run_time_decoding(subject_id, *conditions)
