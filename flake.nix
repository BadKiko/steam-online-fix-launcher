{
  description = "Steam Online Fix Launcher";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      treefmt-nix,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
        pythonPackages =
          ps: with ps; [
            pyyaml
            pillow
            requests
            vdf
            rarfile
            pygobject3
          ];

        soflPackage = import ./packaging/nix/package.nix { inherit pkgs pythonPackages; };
      in
      {
        packages.default = soflPackage;

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            pyright
            black
            (python3.withPackages pythonPackages)

            meson
            ninja
            pkg-config
            cmake
            blueprint-compiler
            gtk4
            libadwaita
            gettext
            glib
            desktop-file-utils
          ];
        };

        formatter = treefmt-nix.lib.mkWrapper nixpkgs.legacyPackages.${system} {
          projectRootFile = "flake.nix";
          programs = {
            nixfmt.enable = true;
            black.enable = true;
            meson.enable = true;
          };
        };
      }
    );
}
