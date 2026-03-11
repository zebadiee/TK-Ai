"""Public kernel entrypoints for TK-Ai."""

from hades.kernel import HadesKernel, build_default_kernel

Kernel = HadesKernel

__all__ = ["Kernel", "build_default_kernel"]
