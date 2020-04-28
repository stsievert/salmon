# Turning off transparent huge-paging is recommended by Redis
# https://redis.io/topics/latency
sudo echo "Running host.sh:"
sudo touch /home/ubuntu/salmon/running-host

sudo echo "    Turning of THP..."
sudo sh -c "echo never > /sys/kernel/mm/transparent_hugepage/enabled"
sudo sh -c "echo never > /sys/kernel/mm/transparent_hugepage/defrag"

## Enable swapping memory to disk to prevent OOM errors
# https://www.digitalocean.com/community/tutorials/how-to-add-swap-space-on-ubuntu-16-04
# Enable swap
sudo echo "    Turning on memory swapping"
sudo fallocate -l 32G /swapfile  # create file
sudo chmod 600 /swapfile  # change permissions
sudo mkswap /swapfile  # mark as swap
sudo swapon /swapfile  # enable swapping

# Make it persist on reboot
sudo echo "    Making memory swap persisent on reboot..."
sudo cp /etc/fstab /etc/fstab.bak
sudo echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
sudo sh -c "echo 'vm.swappiness=10' >> /etc/sysctl.conf "

# From https://stackoverflow.com/questions/44800633/how-to-disable-transparent-huge-pages-thp-in-ubuntu-16-04lts
sudo echo "    Making sure THP is disabled..."
sudo apt install -y hugepages
sudo hugeadm --thp-never
sudo /bin/sed -i '$i /usr/bin/hugeadm --thp-never' /etc/rc.local

sudo echo "Finished running host.sh"
sudo touch /home/ubuntu/salmon/ran-host
