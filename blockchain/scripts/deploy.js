const hre = require("hardhat");
const fs  = require("fs");
const path = require("path");

async function main() {
  console.log("\n================================================");
  console.log("  RefugeeHealthChain - Contract Deployment");
  console.log("  Network:", hre.network.name);
  console.log("  Author: Kevin Mbugua - github mbuguakevvz");
  console.log("================================================\n");

  const [deployer] = await hre.ethers.getSigners();
  const balance    = await hre.ethers.provider.getBalance(deployer.address);

  console.log("Deployer address:", deployer.address);
  console.log("Deployer balance:", hre.ethers.formatEther(balance), "ETH\n");

  console.log("[1/2] Deploying RefugeeRegistry...");
  const RefugeeRegistry = await hre.ethers.getContractFactory("RefugeeRegistry");
  const registry = await RefugeeRegistry.deploy(deployer.address);
  await registry.waitForDeployment();
  const registryAddr = await registry.getAddress();
  console.log("  RefugeeRegistry deployed at:", registryAddr);

  console.log("[2/2] Deploying MedicalRecord...");
  const MedicalRecord = await hre.ethers.getContractFactory("MedicalRecord");
  const medRecord = await MedicalRecord.deploy(deployer.address);
  await medRecord.waitForDeployment();
  const medRecordAddr = await medRecord.getAddress();
  console.log("  MedicalRecord deployed at:", medRecordAddr);

  const deployment = {
    network:     hre.network.name,
    deployedAt:  new Date().toISOString(),
    deployer:    deployer.address,
    contracts: {
      RefugeeRegistry: registryAddr,
      MedicalRecord:   medRecordAddr,
    }
  };

  fs.writeFileSync(
    path.join(__dirname, "..", "..", "deployment.json"),
    JSON.stringify(deployment, null, 2)
  );

  console.log("\n  Deployment info saved to deployment.json");
  console.log("\n  Add these to your .env:");
  console.log("  REFUGEE_REGISTRY_ADDRESS=" + registryAddr);
  console.log("  MEDICAL_RECORD_ADDRESS="   + medRecordAddr);
  console.log("\n================================================");
  console.log("  All contracts deployed successfully!");
  console.log("================================================\n");
}

main().catch((err) => {
  console.error("Deployment failed:", err);
  process.exitCode = 1;
});
