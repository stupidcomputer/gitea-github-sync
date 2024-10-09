{ lib, pkgs, config, ... }:
let
  cfg = config.services.gitea-github-bridge;
  appEnv = pkgs.python3.withPackages (p: with p; [ waitress (callPackage ./bridge/default.nix {}) ]);
in {
  options.services.gitea-github-bridge = {
    enable = lib.mkEnableOption "Enable the Gitea-Github bridge";
  };

  config = lib.mkIf cfg.enable {
    systemd.services.gitea-github-bridge = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        ExecStart = "${appEnv}/bin/waitress-serve --port=8041 bridge:app";
	      StandardOutput = "journal";
      };
    };
  };
}