# Shopify-Theme-Template

This template is meant to be used for all new Shopify projects. It consists of:

- a default Shopify-theme,
- GitHub Actions for Continous Deployment,
- a Python script for supporting the Continous Deployment
by handling all settings updates.

## Instruction
To setup a new Shopify project with this template is really easy. Just follow these steps:

### Create a new repository based on this template repository.
1. Create a new repository.
	![Step 1-1](/images/step-1-1.png)
2. Select this template as repository template.
	![Step 1-2](/images/step-1-2.png)
3. Fill in all other information and save.

### Setup Continous Deployment
In order to setup the continous deployment, you just need to add the API configuration for the targeted Shopify-Shop as repository secrets.
1. Log into the backend of your store (e.g. https://myshop.myshopify.com/admin).
2. Follow this [tutorial](https://shopify.github.io/themekit/#get-api-access) on how to get your API access codes. Ensure you select the stable API version and adjust the variable `shopifyApiVersion` in `shopify-predeploy.py` to reflect the one set for the app.
3. Return to your repository on GitHub and go to `Settings > Secrets`.
	![Step 2-1](/images/step-2-1.png)
4. Click on "New secret" and create the following three secrets:
	![Step 2-2](/images/step-2-2.png)
   1. `SHOPIFY_DOMAIN`: This is the **Shopify domain** of your shop without protocols, leading or trailing spaces, e.g. `myshop.myshopify.com`.
   2. `SHOPIFY_USERNAME`: This is the **API key** you retrieved from your new private app. 
   3. `SHOPIFY_PASSWORD`: This is the **password** you retrieved from your new private app.

And that's it. You've successfully setup your Continous Delivery. Whenever you publish a new branch called "development" or starts with "feature/" (e.g. feature/new-landing-page), GitHub will deploy a theme with a name corresponding to the branch name. 
Whenever you merge a branch into the main branch, it will deploy the new code to the live theme.

### Theme's data
With this tool, we have 2 options to add settings data to the theme, either taking current theme's or live theme's data.
In order to copy live theme's data to the current theme, you need to name your branch with `feature/lt-**` ( by replacing ** with anything, e.g feature/lt-header-update ), and if you want to keep current theme's data you can name the branch `feature/**` (e.g feature/header-update)

### A word of warning
During every deploy, the deployment script download the most recent theme settings from the production theme and applies them to the theme to which you deploy. Therefore, changes to already existing sections in a test theme will be overwritten.

## Advanced topics

### Deploying to multiple servers
In case a customer mirrors their shop but doesn't want to deal with double maintenance, we can deploy the same theme to multiple servers.
All we've got to do is to:

1. Add additional secrets to the repository with the API data for the new shop. Just replace the `XY` in the names of the secrets with a number for the shop (e.g. `SHOPIFY_DOMAIN_2`, `SHOPIFY_USER_2` and `SHOPIFY_PASSWORD_2` for your second store)
    1. `SHOPIFY_DOMAIN_XY`: This is the **Shopify domain** of your shop without protocols, leading or trailing spaces, e.g. `myshop.myshopify.com`.
    1. `SHOPIFY_USER_XY`: This is the **API key** you retrieved from your new private app. 
    2. `SHOPIFY_PASSWORD_XY`: This is the **password** you retrieved from your new private app.
2. Update the deployment scripts
    1. Depending on whether you want to only deploy the main branch to both servers or also the development and feature branches, you'll need to update these files:
        - .github\workflows\deployment-main.yml
        - .github\workflows\deployment-development.yml
	2. Both files contain the code for additional deployment targets as commented section at the bottom. Copy these sections to the jobs list above them, replace `XY` with the same number as for the repository variables above, save and commit.
3. You are done!