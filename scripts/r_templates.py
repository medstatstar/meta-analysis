# -*- coding: utf-8 -*-
# Aggregate entry: materialize all R sources embedded in individual modules.
# 运行期初始化只需执行: python r_templates.py
import os
from r_meta_analysis_core import materialize as _m_core
from r_effect_size_conversions import materialize as _m_esc
from r_network_meta_analysis import materialize as _m_net
from r_setup_packages import materialize as _m_setup
from r_stata_equivalents import materialize as _m_stata
from r_advanced_functions import materialize as _m_adv

MODULES = [_m_core, _m_esc, _m_net, _m_setup, _m_stata, _m_adv]


def materialize_all(scripts_dir=None):
    if scripts_dir is None:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
    return [m(scripts_dir) for m in MODULES]


if __name__ == "__main__":
    for p in materialize_all():
        print("wrote", p)
