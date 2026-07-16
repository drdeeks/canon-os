============================================================================
                     AI CREATIVE STUDIO - USER MANAGEMENT
                      Dual-User Architecture
============================================================================

OVERVIEW
--------
The AI Creative Studio uses a strict two-user model to separate concerns:

  1. CREATOR  -- The content creator. Works through the browser GUI only.
                Cannot break anything. No terminal, no Docker, no sudo.
                Stores models and creations locally on their own drive.

  2. ADMIN    -- The technical operator (DrDeeks). Accesses via SSH only.
                Has zero persistent footprint on the compute brain.
                Manages everything remotely. Nothing saved on compute brain.

This separation protects both parties:
  - The creator cannot accidentally destroy the system.
  - The admin leaves no trace on the compute brain itself.
  - Storage is isolated per user with clear ownership boundaries.


============================================================================
LINUX USER ACCOUNTS
============================================================================

USER: creator
-------------
  Purpose:    Content creator's local account on the compute brain
  UID/GID:    1001 / 1001
  Shell:      /usr/sbin/nologin (NO shell access, ever)
  Home Dir:   /home/creator/
  Groups:     docker (optional, if creator needs to restart containers via GUI)
  Login:      DISABLED for SSH and console
  Password:   NONE (account cannot log in)

  Rationale:
    The creator never opens a terminal. They interact exclusively through
    the browser-based dashboards (Open WebUI, ComfyUI). The nologin shell
    ensures even accidental SSH attempts fail immediately.

  Account creation:
    sudo useradd --uid 1001 --shell /usr/sbin/nologin \
      --home-dir /home/creator --create-home creator
    sudo passwd -l creator   # Lock password


USER: admin
-----------
  Purpose:    Admin's SSH-only management account
  UID/GID:    1002 / 1002
  Shell:      /bin/bash
  Home Dir:   /home/admin/
  Groups:     sudo, docker
  Login:      SSH ONLY (key-based, no password)
  Password:   NONE (key auth only)

  Rationale:
    The admin needs full system access but should never store anything
    persistently on the compute brain. Their home directory exists only
    for SSH session state (authorized_keys, .bashrc). All actual work
    happens over SSH and touches only /mnt/studio/.

  Account creation:
    sudo useradd --uid 1002 --shell /bin/bash \
      --home-dir /home/admin --create-home --groups sudo,docker admin
    sudo passwd -l admin   # Lock password

  SSH hardening for admin:
    - Ed25519 key-based auth only
    - No password authentication
    - fail2ban active
    - See docs/NETWORK-ACCESS.md for full SSH setup


SYSTEM ACCOUNTS (do not modify)
-------------------------------
  ubuntu      UID 1000  -- The original OS user, used by Docker containers
                           (container UID mapping). Leave this alone.
  creator     UID 1001  -- Content creator account (no login)
  admin       UID 1002  -- Admin management account (SSH only)


============================================================================
PER-USER STORAGE PATHS
============================================================================

CREATOR STORAGE: /home/creator/ai-studio/
-----------------------------------------
  This is the creator's LOCAL storage. Models they download and creations
  they generate land here. This is NOT the shared external drive.

  /home/creator/ai-studio/
    |-- models/
    |   |-- text/              # LLM models (GGUF files)
    |   |-- image/             # SDXL, Flux, ControlNet, etc.
    |   |-- video/             # CogVideoX, SVD, AnimateDiff
    |   |-- audio/             # Kokoro, MusicGen, Whisper
    |
    |-- creations/
    |   |-- images/            # Generated images (ComfyUI output)
    |   |-- videos/            # Generated video clips
    |   |-- audio/             # Generated TTS, music
    |   |-- text/              # Generated scripts, copy
    |
    |-- uploads/               # Files uploaded by creator via UI
    |-- cache/                 # Temporary files, download cache
    |-- projects/              # Per-project working directories

  IMPORTANT: This directory lives on the creator's own partition/drive.
  It is NOT the same as /mnt/studio/. See "Storage Isolation" below.


ADMIN STORAGE: /home/admin/ (minimal, temporary only)
------------------------------------------------------
  The admin stores NOTHING on the compute brain. Their home directory
  contains only:
    /home/admin/
      |-- .ssh/
      |   |-- authorized_keys     # SSH public keys
      |-- .bashrc                 # Shell config (optional)
      |-- .bash_history           # Auto-generated (acceptable)

  Admin does NOT use /home/admin/ for:
    - Model storage (use /mnt/studio/)
    - Project files (use /mnt/studio/)
    - Configuration backups (push to external repo)
    - Logs (read from /var/log/ or /mnt/studio/logs/)

  Policy: Admin home directory should remain under 1MB at all times.
  Anything larger indicates accidental data storage.


SHARED EXTERNAL DRIVE: /mnt/studio/
------------------------------------
  This is the shared workspace. Both users (and Docker containers) access
  it, but with different permissions. See "Filesystem ACLs" below.

  /mnt/studio/
    |-- models/                # Shared model library
    |-- projects/              # Shared project storage
    |-- exports/               # Exported final deliverables
    |-- uploads/               # Uploaded source material
    |-- cache/                 # Shared cache
    |-- logs/                  # System and service logs


============================================================================
STORAGE ISOLATION
============================================================================

LOCAL vs SHARED STORAGE
-----------------------
  The creator has TWO separate storage areas:

  1. LOCAL: /home/creator/ai-studio/
     - Creator's personal model cache and creations
     - Protected from admin overwrites
     - Lives on a dedicated partition (never the root drive)
     - Can be synced to /mnt/studio/ if desired

  2. SHARED: /mnt/studio/
     - The official shared workspace
     - Where Docker containers read models and write outputs
     - Admin can manage files here over SSH
     - Creator can read/write via the GUI

  Relationship between them:
    - Creator's local storage is the "working copy"
    - /mnt/studio/ is the "source of truth" for containers
    - Admin manages /mnt/studio/ (downloading models, organizing)
    - Creator accesses everything through the web UIs which
      bind-mount /mnt/studio/ inside containers

  Why this split?
    - If the creator's account is corrupted, /mnt/studio/ survives
    - If admin makes a mistake on /mnt/studio/, creator's local work
      in /home/creator/ai-studio/ is untouched
    - Models can exist in both places (local cache + shared library)


DIRECTORY OWNERSHIP
-------------------
  Path                        Owner       Group       Permissions
  ─────────────────────────── ─────────── ─────────── ───────────
  /home/creator/              creator     creator     750
  /home/creator/ai-studio/    creator     creator     750
  /home/admin/                admin       admin       700
  /mnt/studio/                root        studio      2775
  /mnt/studio/models/         admin       studio      2775
  /mnt/studio/projects/       admin       studio      2775
  /mnt/studio/exports/        admin       studio      2775
  /mnt/studio/uploads/        admin       studio      2775
  /mnt/studio/cache/          admin       studio      2775
  /mnt/studio/logs/           root        studio      2755

  The "studio" group:
    sudo groupadd studio
    sudo usermod -aG studio creator
    sudo usermod -aG studio admin
    sudo chown root:studio /mnt/studio
    sudo chmod 2775 /mnt/studio    # Setgid bit ensures new files inherit group


============================================================================
FILESYSTEM ACLs
============================================================================

PURPOSE
-------
  Standard Unix permissions are too coarse. We use POSIX ACLs to enforce
  fine-grained access control. The goals:

  1. Creator can READ models on /mnt/studio/ (Docker needs this)
  2. Creator can WRITE to projects, exports, uploads on /mnt/studio/
  3. Creator CANNOT touch /etc, /usr, /var, /opt, or any system directory
  4. Creator CANNOT modify other users' home directories
  5. Admin has full access to /mnt/studio/ over SSH
  6. Admin cannot accidentally leave files on the compute brain root


INSTALL ACL TOOLS
-----------------
  sudo apt install acl


SETUP ACLs ON /mnt/studio/
---------------------------

  # Set default ACLs on the parent directory
  sudo setfacl -m u:creator:rwx /mnt/studio/
  sudo setfacl -m u:admin:rwx  /mnt/studio/
  sudo setfacl -m u:creator:rx  /mnt/studio/   # Read-only on root of shared
  sudo setfacl -m u:admin:rwx  /mnt/studio/

  # Creator can read models (container needs this for inference)
  sudo setfacl -R -m u:creator:r-x /mnt/studio/models/
  sudo setfacl -R -d -m u:creator:r-x /mnt/studio/models/

  # Creator can read/write projects (their active work)
  sudo setfacl -R -m u:creator:rwx /mnt/studio/projects/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/projects/

  # Creator can read/write exports (download finished work)
  sudo setfacl -R -m u:creator:rwx /mnt/studio/exports/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/exports/

  # Creator can read/write uploads (upload source material)
  sudo setfacl -R -m u:creator:rwx /mnt/studio/uploads/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/uploads/

  # Creator can write to cache (Docker temp storage)
  sudo setfacl -R -m u:creator:rwx /mnt/studio/cache/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/cache/

  # Creator can only read logs (admin manages these)
  sudo setfacl -R -m u:creator:r-x /mnt/studio/logs/
  sudo setfacl -R -d -m u:creator:r-x /mnt/studio/logs/

  # Admin gets full access to everything
  sudo setfacl -R -m u:admin:rwx /mnt/studio/
  sudo setfacl -R -d -m u:admin:rwx /mnt/studio/

  # Verify
  getfacl /mnt/studio/
  getfacl /mnt/studio/models/
  getfacl /mnt/studio/projects/


LOCK DOWN SYSTEM DIRECTORIES
-----------------------------
  Prevent creator from touching anything outside their home and /mnt/studio/:

  # Creator gets NO access to system directories
  sudo setfacl -m u:creator:--- /etc/
  sudo setfacl -m u:creator:--- /usr/
  sudo setfacl -m u:creator:--- /var/
  sudo setfacl -m u:creator:--- /opt/
  sudo setfacl -m u:creator:--- /root/
  sudo setfacl -m u:creator:--- /boot/
  sudo setfacl -m u:creator:--- /srv/

  # Creator cannot access admin's home directory
  sudo setfacl -m u:creator:--- /home/admin/

  # Admin cannot access creator's home directory (privacy)
  sudo setfacl -m u:admin:--- /home/creator/

  NOTE: The creator's shell is /usr/sbin/nologin, so they cannot execute
  commands. But Docker containers running as creator's UID need filesystem
  access. The ACLs above ensure containers can read/write only permitted
  paths.


SUDOERS RESTRICTIONS
---------------------
  Creator has NO sudo access. Period. No exceptions.

  Admin has LIMITED sudo access restricted to studio management only:

    # /etc/sudoers.d/admin-studio (created by setup-users.sh)
    admin ALL=(root) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose
    admin ALL=(root) NOPASSWD: /usr/local/bin/studio-*
    admin ALL=(root) NOPASSWD: /usr/bin/systemctl restart docker
    admin ALL=(root) NOPASSWD: /usr/bin/systemctl start docker
    admin ALL=(root) NOPASSWD: /usr/bin/systemctl stop docker
    admin ALL=(root) NOPASSWD: /usr/bin/journalctl

  This means admin can:
    - Start/stop/restart Docker containers
    - Run studio-* CLI tools (studio-status, studio-model, studio-doctor)
    - Manage Docker service
    - Read system logs

  Admin CANNOT:
    - Install arbitrary packages
    - Modify system configuration outside Docker/studio
    - Create/delete users
    - Access files outside their permissions

  NOTE: The ACLs on /home/creator/ provide the real hard boundary
  regardless of sudo access.


============================================================================
DASHBOARD ACCESS MODEL
============================================================================

CREATOR DASHBOARD ACCESS
-------------------------
  The creator accesses the system through browser-based dashboards ONLY.
  No SSH. No terminal. No direct file access outside the GUI.

  Access method:
    1. Creator opens laptop (any device with a browser)
    2. Connects to local WiFi or VPN
    3. Opens browser tabs:
       - http://localhost:13000  (Open WebUI -- text AI chat)
       - http://localhost:18188  (ComfyUI -- image/video generation)
       - http://localhost:19000  (Whisper Web -- transcription)

  How it works:
    - Admin sets up SSH tunnels from creator's laptop to compute brain
    - The tunnels forward localhost ports to the compute brain
    - Creator never knows about SSH; they just see local URLs
    - See docs/NETWORK-ACCESS.md for tunnel setup

  What creator can do through the GUI:
    - Chat with text AI (Llama, Gemma)
    - Generate images (Flux, SDXL)
    - Generate video clips (CogVideoX, SVD)
    - Generate voiceovers (Kokoro TTS)
    - Generate music (MusicGen)
    - Transcribe audio (Whisper)
    - Download generated files
    - Upload source material
    - Manage ComfyUI workflows

  What creator CANNOT do:
    - Access a terminal
    - Run Docker commands
    - Modify system configuration
    - Install software
    - Change firewall rules
    - Manage user accounts
    - Access /etc, /usr, /var, etc.
    - Break anything


ADMIN DASHBOARD ACCESS
----------------------
  The admin accesses everything through SSH. No GUI on the admin's machine
  is set up for regular use.

  Access method:
    1. Admin SSHs into compute brain: ssh -p 2222 admin@brain-ip
    2. Has full shell access with sudo
    3. Can also access all dashboards via SSH tunnels:
       ssh -L 13000:localhost:3000 -L 18188:localhost:8188 admin@brain-ip

  What admin can do:
    - Everything (sudo access)
    - Start/stop/restart Docker containers
    - Download and manage models on /mnt/studio/
    - Monitor system health
    - Update software
    - Manage firewall and SSH config
    - View logs
    - Run backups
    - Add/remove users (if needed)
    - Diagnose problems

  What admin should NOT do:
    - Store files in /home/admin/ (policy: keep under 1MB)
    - Modify /home/creator/ (protected by ACLs)
    - Leave the system in an inconsistent state

  Admin "zero footprint" policy:
    - All working files go on /mnt/studio/ or are pushed to external repos
    - No important data in /home/admin/
    - SSH session state is ephemeral
    - If the admin account is deleted, nothing of value is lost


CONTAINER-LEVEL ACCESS
----------------------
  Docker containers run as UID 1000 (the ubuntu user), NOT as creator
  or admin. This is deliberate:

    - UID 1000 is the Docker default mapping
    - Containers can read/write /mnt/studio/ (owned by ubuntu:studio)
    - Containers cannot access /home/creator/ or /home/admin/
    - This provides a clean isolation layer

  If containers need to write to creator's local storage:
    - The container output should go to /mnt/studio/exports/
    - The creator can then download from the GUI
    - We do NOT bind-mount /home/creator/ into containers


============================================================================
ISOLATION BETWEEN LOCAL AND SHARED STORAGE
============================================================================

THREE-STORAGE MODEL
-------------------
  The system has three distinct storage zones:

  1. COMPUTE BRAIN ROOT (/)
     - OS, Docker engine, SSH server
     - Protected by: root ownership, no user write access
     - Nothing creative lives here

  2. CREATOR LOCAL (/home/creator/ai-studio/)
     - Creator's personal working storage
     - Protected by: owner permissions, ACLs
     - NOT used by Docker containers
     - Creator can work offline from this directory

  3. SHARED EXTERNAL (/mnt/studio/)
     - The "official" workspace for Docker containers
     - Protected by: group permissions, ACLs
     - Where all AI inference reads from and writes to
     - Admin manages this over SSH


SYNC BETWEEN LOCAL AND SHARED
------------------------------
  The creator's local storage and /mnt/studio/ are intentionally separate.
  They can be synced manually by the admin if needed:

  # Admin pushes creator's local models to shared storage
  sudo rsync -av /home/creator/ai-studio/models/ /mnt/studio/models/

  # Admin pulls shared exports to creator's local directory
  sudo rsync -av /mnt/studio/exports/ /home/creator/ai-studio/creations/

  # Or use a bidirectional sync tool
  sudo unison /home/creator/ai-studio/projects/ /mnt/studio/projects/

  Why not auto-sync?
    - Avoids conflicts when both Docker and creator write simultaneously
    - Gives admin control over what gets shared
    - Prevents accidental model duplication eating disk space
    - Makes backups simpler (back up /mnt/studio/ only)


EXTERNAL DRIVE ISOLATION
-------------------------
  The external drive at /mnt/studio/ is the system's backbone:
    - Docker containers bind-mount it for model access and output
    - Admin manages it over SSH
    - Creator accesses it indirectly through the GUI
    - Backups target /mnt/studio/ exclusively

  The creator's local /home/creator/ai-studio/ is the "private workspace":
    - Not shared with containers
    - Not backed up by the system backup script
    - Creator's responsibility to back up if desired
    - Safe haven if /mnt/studio/ is accidentally wiped

  Filesystem:
    /mnt/studio/          -- ext4 or xfs on external SSD/NVMe
    /home/creator/        -- ext4 on compute brain's internal drive (or
                             a second external drive if configured)


============================================================================
CONTAINER SECURITY CONTEXT
============================================================================

  Docker containers bridge the creator/admin divide. They must be safe
  for both users:

  Containers run as:
    UID 1000 (ubuntu) -- NOT creator (1001) or admin (1002)

  Containers have:
    - Read-only rootfs
    - All capabilities dropped
    - No privileged mode
    - No-new-privileges
    - Bind-mount of /mnt/studio/ only
    - No access to /home/creator/ or /home/admin/

  This means:
    - If a container is compromised, it cannot touch user home dirs
    - Containers cannot escalate to root
    - Containers can only write to /mnt/studio/ (external drive)
    - The compute brain root is never modified by containers


============================================================================
SETUP COMMANDS SUMMARY
============================================================================

Run these commands to set up the dual-user architecture:

  # 1. Create groups
  sudo groupadd studio
  sudo usermod -aG studio ubuntu   # Docker UID mapping

  # 2. Create creator account (no login)
  sudo useradd --uid 1001 --shell /usr/sbin/nologin \
    --home-dir /home/creator --create-home creator
  sudo usermod -aG studio creator
  sudo passwd -l creator

  # 3. Create admin account (SSH only)
  sudo useradd --uid 1002 --shell /bin/bash \
    --home-dir /home/admin --create-home --groups sudo,docker,studio admin
  sudo passwd -l admin

  # 4. Set up SSH for admin
  sudo mkdir -p /home/admin/.ssh
  sudo chmod 700 /home/admin/.ssh
  # Copy admin's public key to /home/admin/.ssh/authorized_keys
  sudo chmod 600 /home/admin/.ssh/authorized_keys
  sudo chown -R admin:admin /home/admin/.ssh

  # 5. Create creator's local storage
  sudo mkdir -p /home/creator/ai-studio/{models,creations,uploads,cache,projects}
  sudo chown -R creator:creator /home/creator/ai-studio

  # 6. Install ACL tools
  sudo apt install acl

  # 7. Set up /mnt/studio/ ACLs (run after external drive is mounted)
  sudo mkdir -p /mnt/studio/{models,projects,exports,uploads,cache,logs}
  sudo chown root:studio /mnt/studio
  sudo chmod 2775 /mnt/studio

  # Set creator permissions
  sudo setfacl -R -m u:creator:r-x /mnt/studio/models/
  sudo setfacl -R -d -m u:creator:r-x /mnt/studio/models/
  sudo setfacl -R -m u:creator:rwx /mnt/studio/projects/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/projects/
  sudo setfacl -R -m u:creator:rwx /mnt/studio/exports/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/exports/
  sudo setfacl -R -m u:creator:rwx /mnt/studio/uploads/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/uploads/
  sudo setfacl -R -m u:creator:rwx /mnt/studio/cache/
  sudo setfacl -R -d -m u:creator:rwx /mnt/studio/cache/
  sudo setfacl -R -m u:creator:r-x /mnt/studio/logs/
  sudo setfacl -R -d -m u:creator:r-x /mnt/studio/logs/

  # Set admin full access
  sudo setfacl -R -m u:admin:rwx /mnt/studio/
  sudo setfacl -R -d -m u:admin:rwx /mnt/studio/

  # 8. Lock down system directories
  sudo setfacl -m u:creator:--- /etc/ /usr/ /var/ /opt/ /root/ /boot/ /srv/
  sudo setfacl -m u:creator:--- /home/admin/

  # 9. Verify
  id creator
  id admin
  getfacl /mnt/studio/
  getfacl /home/creator/
  getfacl /home/admin/
  ssh admin@localhost echo "Admin SSH works"
  su -s /bin/bash -c "echo test" creator  # Should fail (nologin shell)


============================================================================
TROUBLESHOOTING
============================================================================

Creator cannot save files from the web UI:
  - Check that Docker container UID (1000) has write access to /mnt/studio/
  - Verify: docker exec comfyui ls -la /outputs/
  - Fix: sudo chown -R 1000:studio /mnt/studio/projects/ /mnt/studio/exports/

Admin cannot SSH in:
  - Check /etc/ssh/sshd_config has: AllowUsers admin
  - Verify authorized_keys permissions: 600, owned by admin
  - Check firewall: sudo ufw status
  - Test: ssh -vvv -p 2222 admin@localhost

Creator accidentally got shell access:
  - Verify: getent passwd creator | grep nologin
  - Fix: sudo usermod -s /usr/sbin/nologin creator
  - Check sudoers: sudo grep creator /etc/sudoers /etc/sudoers.d/*

ACLs not working:
  - Install: sudo apt install acl
  - Check filesystem supports ACLs: tune2fs -l /dev/sdX | grep acl
  - Verify: getfacl /mnt/studio/projects/

Disk space issues on creator's home:
  - Check: du -sh /home/creator/ai-studio/*
  - Move models to shared: sudo mv /home/creator/ai-studio/models/* /mnt/studio/models/
  - Or add a second external drive for creator's local storage


============================================================================
DOCUMENT REFERENCES
============================================================================

  ARCHITECTURE.md      -- System overview, model inventory, workflows
  STORAGE-DESIGN.md    -- External drive setup, mounting, backup
  DOCKER-ISOLATION.md  -- Container architecture, compose config
  NETWORK-ACCESS.md    -- SSH setup, tunnels, firewall, remote access


============================================================================
