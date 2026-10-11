# QuickHealth on one AWS EC2 server

This guide prepares one Ubuntu server in **US East (N. Virginia), `us-east-1`** and makes QuickHealth reachable from the public internet, including Nigeria. It uses the AWS web console and the browser-based EC2 Instance Connect option. It does not use AWS CLI.

## Before you launch

- QuickHealth is for fictional cases only. It is a hackathon prototype, not medical advice, and has not been clinically validated. Do not enter real patient information.
- Amazon Bedrock is not available in the hackathon accounts. This setup uses the configured OpenAI API.
- Set an AWS Budget alert in the Billing console before launching, and stop or terminate the instance when finished.
- This prototype saves conversations in a SQLite database on the server. Its saved-session screen is not private between visitors. Do not share this public URL for sensitive use; a visitor may be able to see saved fictional sessions from other visitors.
- Check your hackathon credits or allowance in the AWS Billing console before launching. Choose one small x86-64 instance that the console shows is covered. A `t3.small` (2 GiB RAM) is a practical starting point if your allowance covers it. The smallest `t3.micro` may run out of memory while installing dependencies or serving the app.
- The app is served over HTTP on port 8501, without TLS or a domain name. Anyone who knows the public address can reach it. This guide does not add a login or geographic restriction.
- No AWS cost can be guaranteed here. Check the billing and credits pages, and terminate the instance and remove leftover billable resources when finished.

## 1. Choose the AWS Region

1. Sign in to the AWS web console.
2. Use the Region menu in the upper right and choose **US East (N. Virginia) (`us-east-1`)**.

## 2. Create a security group

The instance needs two inbound rules: port 22 for the AWS browser connection and port 8501 for visitors using the app. Do not create a port 22 rule open to `0.0.0.0/0`.

1. Open **EC2** from the AWS console search bar.
2. In the left menu, choose **Network & Security → Security Groups**, then **Create security group**.
3. Name it `quickhealth-web` and choose the default VPC.
4. Under **Inbound rules**, add:
   - **SSH**, port **22**, source **Custom**: select the prefix list `com.amazonaws.us-east-1.ec2-instance-connect`.
   - **Custom TCP**, port **8501**, source **Anywhere-IPv4** (`0.0.0.0/0`). This is the public app port; it permits connections from Nigeria and other locations without a country filter.
5. Keep the default outbound rule allowing traffic out. The server needs outbound internet access to install packages and contact OpenAI and Neatlogs.
6. Choose **Create security group**.

AWS documents the Instance Connect prefix-list rule in its [browser connection setup guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-tutorial.html).

## 3. Launch one Ubuntu instance

1. In EC2, choose **Instances → Launch instances**.
2. Enter `quickhealth-demo` as the name.
3. Under **Application and OS Images**, choose **Ubuntu**, then an Ubuntu Server 24.04 LTS x86-64 image.
4. Under **Instance type**, select one small size that is covered by your hackathon allowance. Use `t3.small` if covered; otherwise check with the hackathon organizer before choosing a larger type.
5. Under **Key pair (login)**, choose **Proceed without a key pair**. The browser-based EC2 Instance Connect flow supplies its temporary connection key.
6. Under **Network settings**, choose the default VPC and a subnet that assigns a public IPv4 address. Enable **Auto-assign public IP**.
7. Choose **Select existing security group** and select `quickhealth-web`.
8. Under **Configure storage**, keep one modest root volume (for example, 12 GiB) and make sure **Delete on termination** is enabled for it.
9. Check the Summary for one instance, the `us-east-1` Region, and the covered instance type. Choose **Launch instance**.

## 4. Connect in the browser

1. In **EC2 → Instances**, wait for `quickhealth-demo` to show **Running** and pass its status checks.
2. Select it and choose **Connect**.
3. Choose **EC2 Instance Connect**, keep the browser connection option, and choose **Connect**.
4. A browser terminal opens. The commands in the next steps are Linux commands for this server, not AWS commands.

If the browser connection fails, check that inbound port 22 is restricted to the `us-east-1` Instance Connect prefix list and that the instance has a public IPv4 address.

## 5. Download and run the installer

In the browser terminal, download the setup script from this public repository, inspect it, then run it as an administrator. This script installs Python and Git, clones the public repository, installs its Python requirements in a virtual environment, creates the environment-file template, and installs and starts a systemd service.

```bash
curl -fsSL https://raw.githubusercontent.com/dynaayowilliams-dot/quickhealth/main/deploy/aws/setup.sh -o /tmp/quickhealth-setup.sh
less /tmp/quickhealth-setup.sh
sudo bash /tmp/quickhealth-setup.sh
```

The app files are installed in `/opt/quickhealth`. The service starts, but model-backed features will not work until you enter the required values on the server in the next step.

## 6. Enter secrets directly on the server

The checked-in template at `deploy/aws/quickhealth.env.template` lists variable names only. The installer copies it to `/opt/quickhealth/.env` and restricts that file to the `quickhealth` service account. The repository's `.gitignore` excludes `.env`.

1. In the browser terminal, open the server-only file with `sudo nano /opt/quickhealth/.env`.
2. On the server, fill in the values for `OPENAI_API_KEY`, `OPENAI_MODEL`, and `NEATLOGS_API_KEY`. You may also set `QUICKHEALTH_ACCESS_CODE` to a private code for your testers. When set, the app asks for the code before showing saved cases or allowing a new case. Type or paste values directly into this editor. Do not put real values in GitHub, this repository, this README, or a command line.
3. Save in nano with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**.
4. Restart the app service:

   ```bash
   sudo systemctl restart quickhealth
   ```

Never send the key values or access code to anyone or include them in screenshots or support messages. To change a value later, edit this server-only file and restart the service.

## 7. Open the app

1. In the AWS console, open **EC2 → Instances**, select `quickhealth-demo`, and copy its **Public IPv4 address**.
2. In a browser, open `http://PUBLIC-IP:8501`, replacing `PUBLIC-IP` with the copied address.
3. Confirm the QuickHealth banner still says fictional cases only and that it is not medical advice. Do not enter real health information.

The public IPv4 address may change after a stop and start. This setup does not reserve a paid static address.

## If the app does not start

In the browser terminal, inspect service status and recent service logs:

```bash
sudo systemctl status quickhealth --no-pager
sudo journalctl -u quickhealth -n 60 --no-pager
```

The service restarts automatically after a failure. Check that the environment file has all three values, then restart the service. Never paste secret values into logs or support requests.

## Shut everything down when finished

Stop or terminate the instance as soon as the demo is finished. Stopping an instance leaves its disk behind and can continue storage charges. To end this demo and avoid leaving the server online:

1. In the AWS console, open **EC2 → Instances**, select `quickhealth-demo`, then choose **Instance state → Terminate (delete) instance** and confirm.
2. Wait until the instance shows **Terminated**.
3. In **EC2 → Volumes**, check that the root volume was deleted. Delete any unattached volume created for this demo if you no longer need it.
4. In **EC2 → Elastic IPs**, confirm you did not allocate an unused address; release one if you created it and no longer need it.
5. In **EC2 → Security Groups**, delete `quickhealth-web` after no instance uses it.
6. Check **Billing → Bills** and **Credits** for any remaining resources or charges.

Terminating the instance deletes its local SQLite database if the root volume is deleted. AWS explains that preserved EBS volumes continue to incur storage charges in its [volume termination guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/preserving-volumes-on-termination.html).
