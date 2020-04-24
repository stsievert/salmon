# Turning off transparent huge-paging is recommended by Redis
# https://redis.io/topics/latency
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag

## Enable swapping memory to disk to prevent OOM errors
# https://www.digitalocean.com/community/tutorials/how-to-add-swap-space-on-ubuntu-16-04
# Enable swap
sudo fallocate -l 16G /swapfile  # create file
sudo chmod 600 /swapfile  # change permissions
sudo mkswap /swapfile  # mark as swap
sudo swapon /swapfile  # enable swapping

# Make it persist on reboot
sudo cp /etc/fstab /etc/fstab.bak
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
sudo sh -c "echo 'vm.swappiness=10' >> /etc/sysctl.conf "

