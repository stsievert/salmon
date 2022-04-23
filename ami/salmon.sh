# if $DIRECTORY does not exist...
# (which happens when machine is launching for first time)
if [ ! -d "/home/ubuntu/salmon" ]
then
    # Install a working copy of Salmon. This copy on this machine will not be updated
    # (if they want an update, they can start a new machine)
    git clone https://github.com/stsievert/salmon.git /home/ubuntu/salmon
    cd /home/ubuntu/salmon
    git fetch --tags # Get new tags from remote
    latestTag=$(git describe --tags `git rev-list --tags --max-count=1`) # Get latest tag name
    git checkout $latestTag # Checkout latest tag

    cd /home/ubuntu/salmon/ami
    sudo cp salmon.service /lib/systemd/system/
    sudo chmod u+x salmon.sh
    sudo systemctl enable salmon
    sudo systemctl start salmon
    cd /home/ubuntu/salmon

    # Install fresh verison of Docker
    # https://docs.docker.com/install/linux/docker-ce/ubuntu/
    sudo apt-get remove -y docker docker-engine docker.io containerd runc
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io

    # install docker compose
    # https://docs.docker.com/compose/install/
    sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    cd /home/ubuntu/salmon && sudo docker-compose build
fi

sudo sh -c "bash /home/ubuntu/salmon/ami/host.sh"
cd /home/ubuntu/salmon && sudo docker-compose up

# Instructions for deploying to EC2: https://askubuntu.com/questions/919054/how-do-i-run-a-single-command-at-startup-using-systemd
# sudo cp salmon.service /lib/systemd/system/
# sudo chmod u+x salmon.sh
# sudo systemctl start salmon
# sudo systemctl enable salmon
#
## View logs with
# systemctl -l status salmon --lines 2000
