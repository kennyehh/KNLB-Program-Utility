# General Guidelines for master_install.sh

## Intention
 - the intention of this script is to run all distro-specific installation scripts in the same working directory
 - it will scan the directory for "install_*.sh" scripts and execute them in order
 - the intended use is to automate the installation of select distro-specific packages and programs
 - typically this script will be run after a fresh installation of the distro

## Usage
 - the user will place this script in the directory which contains distro-specific installation scripts
 - upon running the script, all the "install_*.sh" scripts in the directory will be executed

## Interface
 - the script will indicate it has started and will display each individual "install_*.sh" script as it is executed
 - the script will display any errors that occur during execution at the end
 - the script will ask the user if they want a log file created and save it if they do in the same working directory
 - if the user chooses to save the log file, it will be saved as "master_install.log" with timestamped entries for each master_install.sh script execution

## Security
 - the script will not execute any "install_*.sh" scripts that are not in the same directory as the master_install.sh script
 - the script will scan the directory for "install_*.sh" scripts and only execute those that are in the same directory as the master_install.sh script
 - the script will scan the "install_*.sh" scripts in the directory for any malicious content before executing them
 - the intention is to safely execute the "install_*.sh" scripts in the directory without causing any harm to the system
 - if the script detects any malicious content in the "install_*.sh" scripts, it will display to the user which scripts contain malicious content and will not execute them
 - if the script detects any malicious content in the "install_*.sh" scripts, it will continue to scan the directory for other "install_*.sh" scripts and execute those that do not contain malicious content

## Specifics
 - this script will be written in Bash and will be compatible with most Linux distributions
 - keep the script simple and easy to read
 - keep the script universal in nature, so it can be used on any Linux distribution
 - make note of the current linux distribution and the native package manager
 - scan each "install_*.sh" script in the directory for any required repositories or package managers that are not native to the current Linux distribution
 - if a required repository or package manager is not native to the current Linux distrubution, skip the installation and notify the user that the installation will not be performed and why it will not be performed

 ## Possible Upgrades
 - When running the master install script, open up a terminal UI which allows the user to select individual "install_*.sh" scripts to execute
 - include options for fonts, configs
 - The UI should detect the current Linux distribution and the native package manager
 - Consider moving away from individual "install_*.sh" scripts and instead have a list of widely known and used programs, and also a place for the user to manually type in the name of a program they wish to install. In both instances - search the distrobution's package manager for the program and install it if it is available. If the program is not available, notify the user and have the user manually enter the installation command for the program
 -
