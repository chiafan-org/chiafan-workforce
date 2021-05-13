{ buildPythonApplication, setuptools, click, flask }:

buildPythonApplication rec {
  pname = "chiafan-workforce";
  version = "0.1.0";

  src = ./.;

  propagatedBuildInputs = [
    setuptools click flask
  ];
}
