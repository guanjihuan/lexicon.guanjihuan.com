#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""控制台输出钉 UTF-8（Windows 默认 GBK 控制台上 ✓/✗/中文会让套件在第一条
断言打印处 UnicodeEncodeError 崩掉；mutation_test.py 曾为此专门两端钉 UTF-8，
本助手把「本进程控制台」这一端收敛成一处）。幂等、失败静默（老解释器无
reconfigure 时退回环境变量方案的使用者不受影响）。"""
import sys


def force_utf8_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
