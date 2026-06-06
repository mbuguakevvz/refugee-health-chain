// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

contract RefugeeRegistry is AccessControl, Pausable {

    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
    bytes32 public constant AUDITOR_ROLE   = keccak256("AUDITOR_ROLE");

    enum DisplacementType { REFUGEE, ASYLUM_SEEKER, IDP, STATELESS, RETURNEE }
    enum RecordStatus     { ACTIVE, SUSPENDED, DECEASED, RETURNED }

    struct RefugeeRecord {
        bytes32  identityHash;
        bytes32  biometricHash;
        string   originCountryISO3;
        string   asylumCountryISO3;
        string   campOrLocation;
        DisplacementType dType;
        RecordStatus     status;
        uint256  registeredAt;
        uint256  lastUpdatedAt;
        address  registeredBy;
        uint256  updateCount;
    }

    mapping(bytes32 => RefugeeRecord) private records;
    mapping(bytes32 => bool)          private identityExists;
    mapping(string  => uint256)       public  refugeeCountByCountry;
    mapping(bytes32 => bytes32[])     private medicalRecordLinks;
    bytes32[] private allRefugeeIds;
    uint256   public  totalRegistered;

    event RefugeeRegistered(
        bytes32 indexed refugeeId,
        string  originCountry,
        string  asylumCountry,
        string  campLocation,
        DisplacementType dType,
        uint256 timestamp
    );

    event RecordUpdated(
        bytes32 indexed refugeeId,
        RecordStatus newStatus,
        uint256 timestamp,
        address updatedBy
    );

    event MedicalHashLinked(
        bytes32 indexed refugeeId,
        bytes32 medicalRecordHash,
        uint256 timestamp
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, admin);
        _grantRole(AUDITOR_ROLE, admin);
    }

    modifier recordExists(bytes32 refugeeId) {
        require(identityExists[refugeeId], "Record not found");
        _;
    }

    function registerRefugee(
        bytes32 identityHash,
        bytes32 biometricHash,
        string  calldata originISO3,
        string  calldata asylumISO3,
        string  calldata camp,
        DisplacementType dType
    ) external onlyRole(REGISTRAR_ROLE) whenNotPaused returns (bytes32 refugeeId) {
        require(!identityExists[identityHash], "Already registered");
        require(bytes(originISO3).length == 3, "Invalid origin ISO3");
        require(bytes(asylumISO3).length == 3, "Invalid asylum ISO3");

        refugeeId = keccak256(abi.encodePacked(
            identityHash, biometricHash, block.timestamp, block.chainid
        ));

        records[refugeeId] = RefugeeRecord({
            identityHash:      identityHash,
            biometricHash:     biometricHash,
            originCountryISO3: originISO3,
            asylumCountryISO3: asylumISO3,
            campOrLocation:    camp,
            dType:             dType,
            status:            RecordStatus.ACTIVE,
            registeredAt:      block.timestamp,
            lastUpdatedAt:     block.timestamp,
            registeredBy:      msg.sender,
            updateCount:       0
        });

        identityExists[identityHash] = true;
        allRefugeeIds.push(refugeeId);
        refugeeCountByCountry[asylumISO3]++;
        totalRegistered++;

        emit RefugeeRegistered(refugeeId, originISO3, asylumISO3, camp, dType, block.timestamp);
        return refugeeId;
    }

    function updateStatus(
        bytes32 refugeeId,
        RecordStatus newStatus
    ) external onlyRole(REGISTRAR_ROLE) whenNotPaused recordExists(refugeeId) {
        RefugeeRecord storage rec = records[refugeeId];
        if (newStatus == RecordStatus.RETURNED && rec.status == RecordStatus.ACTIVE) {
            if (refugeeCountByCountry[rec.asylumCountryISO3] > 0) {
                refugeeCountByCountry[rec.asylumCountryISO3]--;
            }
        }
        rec.status        = newStatus;
        rec.lastUpdatedAt = block.timestamp;
        rec.updateCount++;
        emit RecordUpdated(refugeeId, newStatus, block.timestamp, msg.sender);
    }

    function linkMedicalRecord(
        bytes32 refugeeId,
        bytes32 medicalHash
    ) external onlyRole(REGISTRAR_ROLE) whenNotPaused recordExists(refugeeId) {
        medicalRecordLinks[refugeeId].push(medicalHash);
        records[refugeeId].lastUpdatedAt = block.timestamp;
        records[refugeeId].updateCount++;
        emit MedicalHashLinked(refugeeId, medicalHash, block.timestamp);
    }

    function verifyIdentity(bytes32 identityHash) external view returns (bool) {
        return identityExists[identityHash];
    }

    function getRecordLocation(bytes32 refugeeId) external view
        onlyRole(AUDITOR_ROLE) recordExists(refugeeId)
        returns (string memory, string memory, string memory)
    {
        RefugeeRecord storage rec = records[refugeeId];
        return (rec.originCountryISO3, rec.asylumCountryISO3, rec.campOrLocation);
    }

    function getRecordStatus(bytes32 refugeeId) external view
        onlyRole(AUDITOR_ROLE) recordExists(refugeeId)
        returns (DisplacementType, RecordStatus, uint256, uint256, uint256)
    {
        RefugeeRecord storage rec = records[refugeeId];
        return (rec.dType, rec.status, rec.registeredAt, rec.updateCount, medicalRecordLinks[refugeeId].length);
    }

    function getCountByCountry(string calldata iso3) external view returns (uint256) {
        return refugeeCountByCountry[iso3];
    }

    function pause()   external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
