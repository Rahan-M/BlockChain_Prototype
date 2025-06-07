{ pkgs ? import <nixpkgs> {} }: # if pkgs was passed in use that or use the builtin nixpkgs

pkgs.mkShell {
  buildInputs = [
    (pkgs.python311.withPackages (ps: with ps; [
      flask
      cryptography
      cffi
      ecdsa
      websockets
      six
    ]))
  ];
}

# mkShell is a function from the pkgs package set that creates a development shell environment.
# It takes an attribute set (a set of key-value pairs) that configures the shell environment.
# This means when you run nix-shell in this directory, Nix uses this to prepare your environment.

#buildInputs = [ ... ]
#buildInputs is a list of packages or dependencies that the shell should provide.
#These packages become available inside the nix-shell environment.
#In this case, it’s a list with one item: a Python environment with specific Python packages.

# (pkgs.python311.withPackages (ps: with ps; [ ... ]))
# pkgs.python311 refers to Python version 3.11 from Nixpkgs.
# .withPackages is a function to create a Python interpreter preloaded with specific Python packages.
# It takes a function as an argument: (ps: with ps; [ ... ])

#5. (ps: with ps; [ flask cryptography cffi ecdsa websockets six ])
# Here, ps represents the Python package set for Python 3.11 inside Nixpkgs.

# with ps; means: “import all these packages’ names into this scope, so you can list them directly.”
# The list [ flask cryptography cffi ecdsa websockets six ] contains the Python packages you want included in your environment.
# Nix will ensure those Python packages and their dependencies are installed in this shell’s Python interpreter.