{
  description = "Tools for chia plotting and farminge";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-20.09";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: flake-utils.lib.eachSystem [
    "x86_64-linux" "i686-linux" "aarch64-linux"
  ] (system:
    let pkgs = import nixpkgs {
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
          (pkgs.writeCBin "chiaplot1" ''
             #include <stdio.h>
             #include <unistd.h>
             #include <time.h>
             int main(int argc, char **argv) {
               FILE *f = fopen("/home/breakds/Downloads/20210508_23_12_27.log", "r");
               char *line;
               size_t len = 0;
               ssize_t read;
               struct timespec ts;
               ts.tv_sec = 0;
               ts.tv_nsec = 200000000;  // 200 ms
               while ((read = getline(&line, &len, f)) != -1) {
                 printf("%s\n", line);
                 nanosleep(&ts, NULL);
               }
               fclose(f);
               return 0;
             }
           '')
        ];
      };
    });
}
