Generates a file with the public IPs of public cloud providers

For AWS, Azure, Google and Oracle it accesses their prescribed URLS or DNS (for GCP)

For DigitalOcean and OVH it uses a BGP query

For alibaba it uses a local file with the IPs specified - alibaba_ips.txt

New providers can be added by modifying the source code.

