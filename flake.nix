{
  description = "Tools for chia plotting and farminge";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-20.09";
    flake-utils.url = "github:numtide/flake-utils";
    plotting-simulator.url = "github:chiafan-org/plotting-simulator";
  };

  outputs = { self, nixpkgs, flake-utils, plotting-simulator, ... }:  let supportedLinuxSystems = [
    "x86_64-linux" "i686-linux" "aarch64-linux"
  ]; in {
    overlay = final: prev: {
      python3 = prev.python3.override {
        packageOverrides = python-final: python-prev: {
          chiafan-workforce = python-final.callPackage ./default.nix {};
        };
      };
    };
  } // flake-utils.lib.eachSystem supportedLinuxSystems (system:
    let pkgs = import nixpkgs {
          overlays = [
            plotting-simulator.overlay
            self.overlay
          ];
          inherit system;
        };

        chiafan-py-dev = pkgs.python3.withPackages (python-packages: with python-packages;  [
          setuptools
          click
          flask
        ]);
    in {
      devShell = pkgs.mkShell rec {
        name = "chiafan-dev";
        buildInputs = with pkgs; [
          chiafan-py-dev
          python3Packages.chiafan-plot-sim
        ];
      };

      defaultPackage = pkgs.python3Packages.chiafan-workforce;
    });
}
