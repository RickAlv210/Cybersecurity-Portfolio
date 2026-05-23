import requests
import json
from datetime import datetime

# === CONFIGURATION ===
API_KEY = "YOUR_VT_API_KEY_HERE"
BASE_URL = "https://www.virustotal.com/api/v3"

HEADERS = {
    "x-apikey": API_KEY
}

# === IOCs TO CHECK ===
iocs = {
    "ips": [
        "8.8.8.8",
        "185.220.101.45"
    ],
    "hashes": [
        "44d88612fea8a8f36de82e1278abb02f"
    ]
}

# === IP LOOKUP FUNCTION ===
def check_ip(ip):
    url = f"{BASE_URL}/ip_addresses/{ip}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]
        result = {
            "ioc": ip,
            "type": "IP",
            "malicious": stats["malicious"],
            "suspicious": stats["suspicious"],
            "harmless": stats["harmless"],
            "undetected": stats["undetected"]
        }
        return result
    else:
        return {"ioc": ip, "type": "IP", "error": f"Status code {response.status_code}"}

# === HASH LOOKUP FUNCTION ===
def check_hash(file_hash):
    url = f"{BASE_URL}/files/{file_hash}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]
        result = {
            "ioc": file_hash,
            "type": "HASH",
            "malicious": stats["malicious"],
            "suspicious": stats["suspicious"],
            "harmless": stats["harmless"],
            "undetected": stats["undetected"]
        }
        return result
    else:
        return {"ioc": file_hash, "type": "HASH", "error": f"Status code {response.status_code}"}

# === REPORT GENERATOR ===
def generate_report(results):
    report = {
        "report_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_iocs_checked": len(results),
        "findings": results
    }
    
    filename = f"ioc_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w") as f:
        json.dump(report, f, indent=4)
    
    print(f"\n[+] Report saved as: {filename}")
    return report

# === PRINT SUMMARY TO TERMINAL ===
def print_summary(results):
    print("\n" + "="*50)
    print("       IOC CHECKER — SCAN SUMMARY")
    print("="*50)
    
    for r in results:
        if "error" in r:
            print(f"\n[ERROR] {r['ioc']} — {r['error']}")
        else:
            status = "🔴 MALICIOUS" if r["malicious"] > 0 else "🟢 CLEAN"
            print(f"\n[{r['type']}] {r['ioc']}")
            print(f"  Status     : {status}")
            print(f"  Malicious  : {r['malicious']}")
            print(f"  Suspicious : {r['suspicious']}")
            print(f"  Harmless   : {r['harmless']}")
            print(f"  Undetected : {r['undetected']}")
    
    print("\n" + "="*50)

# === MAIN EXECUTION ===
def main():
    print("\n[*] Starting IOC Checker...")
    print(f"[*] Scanning {len(iocs['ips'])} IPs and {len(iocs['hashes'])} hashes\n")
    
    results = []
    
    # Check IPs
    for ip in iocs["ips"]:
        print(f"[*] Checking IP: {ip}")
        result = check_ip(ip)
        results.append(result)
    
    # Check Hashes
    for file_hash in iocs["hashes"]:
        print(f"[*] Checking Hash: {file_hash}")
        result = check_hash(file_hash)
        results.append(result)
    
    # Print summary and generate report
    print_summary(results)
    generate_report(results)
    
    print("\n[✓] Scan complete.")

if __name__ == "__main__":
    main()
