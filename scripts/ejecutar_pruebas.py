"""Ejecuta unittest y guarda evidencia; --cobertura requiere coverage como herramienta de desarrollo."""

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path


class ResultadoContado(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtests = 0
        self.exhaustive = 0
        self.timings = []

    def addSubTest(self, test, subtest, err):
        self.subtests += 1
        if test.__class__.__module__ == "test_exhaustivos":
            self.exhaustive += 1
        super().addSubTest(test, subtest, err)

    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        self.timings.append({"test": test.id(), "seconds": time.perf_counter() - self.started})
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default="informes/pruebas-core", type=Path)
    parser.add_argument("--cobertura", action="store_true")
    opciones = parser.parse_args()
    raiz = Path(__file__).resolve().parents[1]
    os.chdir(raiz)
    sys.path.insert(0, str(raiz))
    salida = opciones.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    cov = None
    version_coverage = None
    if opciones.cobertura:
        try:
            import coverage
        except ImportError:
            parser.error("--cobertura requiere instalar coverage; la ejecución normal solo usa unittest.")
        version_coverage = coverage.__version__
        cov = coverage.Coverage(branch=True, source=["arboles_de_red"], config_file=False, data_file=None)
        cov.set_option("run:relative_files", True)
        cov.start()
    suite = unittest.defaultTestLoader.discover("tests")
    inicio = time.perf_counter()
    with (salida / "ejecucion.txt").open("w", encoding="utf-8") as log:
        resultado = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=ResultadoContado).run(suite)
    segundos = time.perf_counter() - inicio
    if cov is not None:
        cov.stop()
        cov.json_report(outfile=str(salida / "cobertura.json"))
        with (salida / "cobertura.txt").open("w", encoding="utf-8") as log:
            cov.report(file=log, show_missing=True)
    resumen = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "coverage_version": version_coverage,
        "tests": resultado.testsRun,
        "subtests": resultado.subtests,
        "exhaustive_subtests": resultado.exhaustive,
        "failures": len(resultado.failures),
        "errors": len(resultado.errors),
        "skipped": len(resultado.skipped),
        "successful": resultado.wasSuccessful(),
        "seconds": segundos,
        "timings": resultado.timings,
    }
    for nombre, carpeta in (("source_sha256", "arboles_de_red"), ("test_sha256", "tests")):
        resumen[nombre] = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(Path(carpeta).glob("*.py"))}
    (salida / "resultado.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Tests: {resultado.testsRun}; subcasos: {resultado.subtests}; "
          f"fallos: {len(resultado.failures)}; errores: {len(resultado.errors)}; "
          f"omitidos: {len(resultado.skipped)}; segundos: {segundos:.3f}.")
    print(f"Evidencia: {salida}")
    if not resultado.wasSuccessful():
        print((salida / "ejecucion.txt").read_text(encoding="utf-8")[-18000:])
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
