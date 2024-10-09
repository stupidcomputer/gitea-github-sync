{ pkgs, pythonPackages ? (import <nixpkgs> {}).python3Packages }:
pythonPackages.buildPythonPackage {
  name = "gitea-github-bridge";
  src = ./bridge;

  propagatedBuildInputs = [ pythonPackages.flask pythonPackages.requests ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/${pythonPackages.python.sitePackages}
    cp -r . $out/${pythonPackages.python.sitePackages}/bridge

    runHook postInstall
  '';

  shellHook = "export FLASK_APP=bridge";

  format = "other";
}