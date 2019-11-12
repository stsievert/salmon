## Salmon

## Getting started
### Experimentalists

1. Go to https://github.com/nextml/next//wiki/AMI-launch for basic information.
   These instructions largely follow those instructions; they are different in
   several key ways (the AMI, networking rules and URL).
1. Go to Amazon AWS EC2
1. Select the "Oregon" region (or `us-west-2`)
1. Launch a new instance. Select AMI `ami-06ec58f46ec2d18ea` titled "Salmon"
   (appears in Community AMIs after searching).
1. On the rules page,  rules:

![](ami/networking-rule.png)

After finished launching and initializing, go to `[url]:8000/init_exp` and
`[url]:8000/docs` where `[url]` is the public DNS or pubic IP.

### Developer

1. Install docker
2. Run `docker-compose up`
3. Go to `localhost:8000/init_exp`
