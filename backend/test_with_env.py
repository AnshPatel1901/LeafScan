#!/usr/bin/env python
"""Test the prediction pipeline with proper env setup."""
import os
import sys

# Set env vars BEFORE any other imports
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Now run the test
exec(open('test_pipeline.py').read())
