{ pkgs, pythonPackages }:

pkgs.stdenv.mkDerivation {
  pname = "sofl";
  version = "0.0.3.3a";
  src = ../../.;
  nativeBuildInputs = with pkgs; [
    meson
    ninja
    pkg-config
    blueprint-compiler
    gettext
    glib
    wrapGAppsHook
    desktop-file-utils
  ];
  buildInputs = with pkgs; [
    gtk4
    libadwaita
    (python3.withPackages pythonPackages)
    unrar
  ];
  mesonFlags = [
    "-Dprofile=release"
    "-Dtiff_compression=webp"
  ];
  postInstall = ''
    wrapProgram $out/bin/sofl \
      --prefix PATH : ${pkgs.unrar}/bin
  '';
}
