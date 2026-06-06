// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

contract MedicalRecord is AccessControl, Pausable {

    bytes32 public constant HEALTH_WORKER_ROLE = keccak256("HEALTH_WORKER_ROLE");
    bytes32 public constant AUDITOR_ROLE       = keccak256("AUDITOR_ROLE");

    enum RecordType {
        VACCINATION,
        DIAGNOSIS,
        TREATMENT,
        LAB_RESULT,
        OUTBREAK_EXPOSURE,
        MENTAL_HEALTH,
        NUTRITION,
        GENERAL_CHECKUP
    }

    struct MedicalEntry {
        bytes32    refugeeId;
        bytes32    recordHash;
        bytes32    ipfsCidHash;
        RecordType rType;
        string     facilityISO3;
        string     facilityName;
        string     diseaseCode;
        uint256    createdAt;
        address    createdBy;
        bool       isVerified;
        address    verifiedBy;
    }

    mapping(bytes32 => MedicalEntry) private entries;
    mapping(bytes32 => bytes32[])    private refugeeEntries;
    mapping(bytes32 => bool)         private recordHashExists;
    mapping(string  => bytes32[])    private outbreakExposures;

    uint256 public totalRecordsAnchored;
    mapping(RecordType => uint256) public recordsByType;

    event MedicalRecordAnchored(
        bytes32 indexed entryId,
        bytes32 indexed refugeeId,
        RecordType rType,
        string diseaseCode,
        string facility,
        uint256 timestamp
    );

    event RecordVerified(
        bytes32 indexed entryId,
        address verifiedBy,
        uint256 timestamp
    );

    event OutbreakExposureLogged(
        bytes32 indexed refugeeId,
        string indexed outbreakId,
        uint256 timestamp
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(HEALTH_WORKER_ROLE, admin);
        _grantRole(AUDITOR_ROLE, admin);
    }

    function anchorRecord(
        bytes32    refugeeId,
        bytes32    recordHash,
        bytes32    ipfsCidHash,
        RecordType rType,
        string calldata facilityISO3,
        string calldata facilityName,
        string calldata diseaseCode
    ) external onlyRole(HEALTH_WORKER_ROLE) whenNotPaused returns (bytes32 entryId) {
        require(!recordHashExists[recordHash],    "Hash already anchored");
        require(bytes(facilityISO3).length == 3, "Invalid facility ISO3");

        entryId = keccak256(abi.encodePacked(
            refugeeId, recordHash, block.timestamp, msg.sender
        ));

        entries[entryId] = MedicalEntry({
            refugeeId:    refugeeId,
            recordHash:   recordHash,
            ipfsCidHash:  ipfsCidHash,
            rType:        rType,
            facilityISO3: facilityISO3,
            facilityName: facilityName,
            diseaseCode:  diseaseCode,
            createdAt:    block.timestamp,
            createdBy:    msg.sender,
            isVerified:   false,
            verifiedBy:   address(0)
        });

        recordHashExists[recordHash] = true;
        refugeeEntries[refugeeId].push(entryId);
        totalRecordsAnchored++;
        recordsByType[rType]++;

        if (rType == RecordType.OUTBREAK_EXPOSURE && bytes(diseaseCode).length > 0) {
            outbreakExposures[diseaseCode].push(refugeeId);
            emit OutbreakExposureLogged(refugeeId, diseaseCode, block.timestamp);
        }

        emit MedicalRecordAnchored(entryId, refugeeId, rType, diseaseCode, facilityName, block.timestamp);
        return entryId;
    }

    function verifyRecord(bytes32 entryId)
        external onlyRole(HEALTH_WORKER_ROLE) whenNotPaused
    {
        MedicalEntry storage entry = entries[entryId];
        require(entry.createdAt > 0,           "Entry not found");
        require(!entry.isVerified,             "Already verified");
        require(entry.createdBy != msg.sender, "Cannot self-verify");

        entry.isVerified = true;
        entry.verifiedBy = msg.sender;

        emit RecordVerified(entryId, msg.sender, block.timestamp);
    }

    function verifyRecordHash(bytes32 recordHash) external view returns (bool) {
        return recordHashExists[recordHash];
    }

    function getOutbreakExposureCount(string calldata outbreakId)
        external view returns (uint256)
    {
        return outbreakExposures[outbreakId].length;
    }

    function getEntry(bytes32 entryId) external view
        onlyRole(AUDITOR_ROLE)
        returns (bytes32, RecordType, string memory, string memory, uint256, bool)
    {
        MedicalEntry storage e = entries[entryId];
        require(e.createdAt > 0, "Not found");
        return (e.refugeeId, e.rType, e.facilityName, e.diseaseCode, e.createdAt, e.isVerified);
    }

    function pause()   external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
