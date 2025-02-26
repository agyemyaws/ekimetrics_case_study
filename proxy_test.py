import requests
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse


def test_proxy(proxy, test_url='https://httpbin.org/ip', timeout=10):
    """
    Test if a proxy works by trying to connect to a test URL

    Args:
        proxy (str): Proxy URL in format "http://host:port" or "http://user:pass@host:port"
        test_url (str): URL to test connection (default uses httpbin to return your IP)
        timeout (int): Connection timeout in seconds

    Returns:
        dict: Test results including success status, response time, and IP info
    """
    # Format proxy with http:// prefix if not already present
    if not proxy.startswith('http'):
        proxy = f"http://{proxy}"

    proxies = {
        'http': proxy,
        'https': proxy
    }

    start_time = time.time()
    result = {
        'proxy': proxy,
        'working': False,
        'response_time': None,
        'ip': None,
        'error': None
    }

    try:
        # Try to make a request through the proxy
        response = requests.get(test_url, proxies=proxies, timeout=timeout)

        # Calculate response time
        result['response_time'] = time.time() - start_time

        # Check if request was successful
        if response.status_code == 200:
            result['working'] = True
            result['ip'] = response.json().get('origin', 'Unknown')
        else:
            result['error'] = f"HTTP Error: {response.status_code}"

    except requests.exceptions.Timeout:
        result['error'] = "Timeout Error"
    except requests.exceptions.ProxyError:
        result['error'] = "Proxy Connection Error"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result


def test_proxy_list(proxy_list, concurrent=True, max_workers=10):
    """
    Test a list of proxies and return results

    Args:
        proxy_list (list): List of proxy strings
        concurrent (bool): Whether to test proxies concurrently
        max_workers (int): Maximum number of concurrent workers if concurrent=True

    Returns:
        pandas.DataFrame: Results of proxy tests
    """
    results = []

    # Print original IP for reference
    try:
        original_ip = requests.get('https://httpbin.org/ip', timeout=10).json().get('origin', 'Unknown')
        print(f"Your original IP: {original_ip}")
    except Exception as e:
        print(f"Could not determine your original IP: {str(e)}")

    if concurrent:
        print(f"Testing {len(proxy_list)} proxies concurrently with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxy_list}
            completed = 0
            for future in as_completed(future_to_proxy):
                completed += 1
                if completed % 10 == 0:  # Progress update every 10 proxies
                    print(f"Tested {completed}/{len(proxy_list)} proxies...")
                try:
                    result = future.result()
                    results.append(result)
                    # Print working proxies immediately
                    if result['working']:
                        print(
                            f"✅ Working proxy found: {result['proxy']} - Response time: {result['response_time']:.2f}s")
                except Exception as e:
                    print(f"Error testing proxy: {str(e)}")
    else:
        print(f"Testing {len(proxy_list)} proxies sequentially...")
        for i, proxy in enumerate(proxy_list):
            print(f"Testing proxy {i + 1}/{len(proxy_list)}: {proxy}")
            result = test_proxy(proxy)
            results.append(result)

            # Print result
            if result['working']:
                print(f"✅ Working! Response time: {result['response_time']:.2f}s, IP: {result['ip']}")
            else:
                print(f"❌ Failed: {result['error']}")

    # Convert results to DataFrame for easier analysis
    df = pd.DataFrame(results)

    # Calculate summary statistics
    working_count = df['working'].sum()
    total_count = len(df)

    print(f"\nProxy Test Results:")
    print(f"Working proxies: {working_count}/{total_count} ({working_count / total_count * 100:.1f}%)")

    if working_count > 0:
        working_df = df[df['working'] == True]
        print(f"Average response time: {working_df['response_time'].mean():.2f}s")

        # Find and print fastest proxy
        if not working_df.empty:
            fastest_idx = working_df['response_time'].idxmin()
            if fastest_idx is not None:
                fastest_proxy = working_df.loc[fastest_idx]['proxy']
                print(f"Fastest proxy: {fastest_proxy} ({working_df.loc[fastest_idx]['response_time']:.2f}s)")

    return df


def test_google_trends_access(proxy_list, timeout=15):
    """
    Test access to Google Trends specifically

    Args:
        proxy_list (list): List of proxy strings that are already confirmed working
        timeout (int): Connection timeout in seconds

    Returns:
        pandas.DataFrame: Results of Google Trends access tests
    """
    results = []
    test_url = 'https://trends.google.com/trends/explore'

    print(f"\nTesting Google Trends access for {len(proxy_list)} working proxies...")

    for proxy in proxy_list:
        if not proxy.startswith('http'):
            proxy = f"http://{proxy}"

        proxies = {
            'http': proxy,
            'https': proxy
        }

        result = {
            'proxy': proxy,
            'google_trends_access': False,
            'response_time': None,
            'error': None
        }

        try:
            start_time = time.time()
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            result['response_time'] = time.time() - start_time

            if response.status_code == 200:
                result['google_trends_access'] = True
                print(f"✅ Google Trends accessible via: {proxy} ({result['response_time']:.2f}s)")
            else:
                result['error'] = f"HTTP Error: {response.status_code}"
                print(f"❌ Cannot access Google Trends via {proxy}: {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Cannot access Google Trends via {proxy}: {result['error']}")

        results.append(result)

    return pd.DataFrame(results)


# Load the proxy list from the provided text
def load_proxies_from_text(text):
    """Load proxies from text content"""
    # Split by newlines and filter out empty lines
    proxies = [line.strip() for line in text.split('\n') if line.strip()]
    return proxies


# Main function to run the tests
def main():
    # Sample proxy list from https://free-proxy-list.net/
    proxy_text = """23.82.137.156:80
85.215.64.49:80
219.65.73.81:80
150.136.247.129:1080
23.247.137.142:80
50.174.7.159:80
50.207.199.87:80
32.223.6.94:80
82.119.96.254:80
78.129.155.75:8080
197.255.126.69:80
44.218.183.55:80
44.195.247.145:80
50.207.199.80:80
50.207.199.83:80
50.174.7.153:80
50.202.75.26:80
50.169.37.50:80
50.232.104.86:80
50.239.72.18:80
50.175.212.66:80
50.217.226.47:80
50.239.72.16:80
50.217.226.40:80
50.221.74.130:80
190.58.248.86:80
50.207.199.82:80
50.174.7.152:80
50.122.86.118:80
66.191.31.158:80
103.152.112.120:80
184.169.154.119:80
13.56.192.187:80
188.40.59.208:3128
83.217.23.35:8090
23.247.136.245:80
23.247.136.248:80
23.247.136.254:80
103.152.112.157:80
35.72.118.126:80
104.238.160.36:80
3.122.84.99:3128
43.202.154.212:80
3.37.125.76:3128
18.228.149.161:80
18.185.169.150:3128
3.139.242.184:80
43.200.77.128:3128
43.201.121.81:80
54.233.119.172:3128
52.196.1.182:80
18.228.198.164:80
52.67.10.183:80
43.154.134.238:50001
45.144.64.153:8080
77.232.128.191:80
43.129.201.43:443
103.152.112.159:80
204.236.176.61:3128
103.152.112.195:80
51.16.199.206:3128
13.48.109.48:3128
13.246.209.48:1080
52.63.129.110:3128
54.179.39.14:3128
99.80.11.54:3128
51.20.50.149:3128
15.156.24.206:3128
13.213.114.238:3128
3.97.176.251:3128
3.97.167.115:3128
51.16.179.113:1080
63.32.1.88:3128
54.179.44.51:3128
16.16.239.39:3128
51.20.19.159:3128
31.47.58.37:80
3.141.217.225:80
51.68.175.56:1080
5.106.6.235:80
3.90.100.12:80
54.248.238.110:80
50.169.222.243:80
50.169.222.241:80
63.35.64.177:3128
84.39.112.144:3128
52.73.224.54:3128
44.219.175.186:80
13.59.140.31:8888
219.93.101.60:80
50.207.199.86:80
139.162.78.109:8080
87.248.129.26:80
211.128.96.206:80
68.185.57.66:80
50.231.104.58:80
50.207.199.81:80
127.0.0.7:80
143.42.191.48:80
3.127.121.101:80
46.173.211.221:12880
45.161.201.203:3386
50.217.226.41:80
171.248.101.145:3712
168.196.114.89:56000
109.165.192.55:8181
38.156.233.132:999
103.48.69.170:83
180.190.200.107:8082
45.181.123.25:999
103.115.239.14:1111
159.203.61.169:3128
40.71.46.210:8214
67.43.228.254:8091
18.223.25.15:80
50.223.246.237:80
41.207.187.178:80
72.10.160.94:18549
13.37.59.99:3128
13.38.176.104:3128
13.36.87.105:3128
13.37.73.214:80
50.239.72.19:80
37.187.25.85:80
43.163.87.93:8080
13.208.56.180:80
3.126.147.182:80
35.79.120.242:3128
3.124.133.93:3128
46.51.249.135:3128
3.78.92.159:3128
54.37.214.253:8080
103.152.112.186:80
52.65.193.254:3128
54.228.164.102:3128
123.30.154.171:7777
3.212.148.199:3128
15.206.189.233:3128
51.254.78.223:80
204.236.137.68:80
87.248.129.32:80
158.160.52.208:8090
162.223.90.130:80
0.0.0.0:80
97.74.87.226:80
50.174.7.156:80
66.29.154.103:3128
46.209.199.145:8090
103.152.238.115:1080
41.254.63.18:8080
66.54.106.56:8102
202.131.153.146:1111
180.191.59.109:8082
58.69.125.145:8081
47.245.37.87:3389
103.123.168.202:3932
1.10.229.85:8080
54.67.125.45:3128
108.62.60.32:3128
200.174.198.86:8888
3.12.144.146:3128
13.59.156.167:3128
216.229.112.25:8080
13.38.153.36:80
13.36.104.85:80
13.36.113.81:3128
180.210.89.215:3128
50.175.212.74:80
123.30.184.101:8889
3.127.62.252:80
3.21.101.158:3128
3.129.184.210:80
51.17.58.162:3128
52.16.232.164:3128
143.42.66.91:80
198.49.68.80:80
133.18.234.13:80
27.147.129.26:58080
114.141.50.211:8080
47.176.240.250:4228
36.253.18.38:8181
58.64.12.11:8081
190.26.255.30:999
103.82.132.206:36729
5.189.174.81:8888
143.198.226.25:80
141.11.103.136:8080
67.43.227.226:11305
13.37.89.201:80
15.236.106.236:3128
3.9.71.167:1080
8.210.232.181:7888
47.243.113.74:5555
27.147.215.56:13457
3.130.65.162:3128
38.126.132.242:3128
62.205.169.74:53281
63.143.57.116:80
195.114.209.50:80
13.246.184.110:3128
158.255.77.169:80
198.74.51.79:8888
66.29.154.105:3128
134.209.29.120:3128
47.56.110.204:8989
47.251.43.115:33333
4.175.200.138:8080
144.126.216.57:80
103.76.151.74:8089
188.136.162.47:7060
65.182.3.154:8080
186.180.22.196:8080
24.152.58.138:999
93.126.6.68:3128
103.146.184.134:8080
103.162.36.13:8080
8.213.211.216:63128
47.91.120.190:3128
89.116.34.113:80
63.143.57.117:80
39.109.113.97:4090
18.135.133.116:1080
23.82.137.158:80
115.72.9.250:10003
138.68.235.51:80
165.232.129.150:80
116.125.141.115:80
81.169.213.169:8888
46.47.197.210:3128
45.140.143.77:18080
203.115.101.53:82
138.68.60.8:8080
47.88.59.79:82
113.160.133.32:8080
41.59.90.171:80
23.88.116.40:80
147.135.128.218:80
192.73.244.36:80
190.103.177.131:80
119.18.147.179:96
113.23.195.5:1231
103.151.140.124:10609
102.68.128.212:8080
179.49.117.21:999
59.28.174.162:3055
58.147.186.31:3125
202.154.18.1:4995
104.225.220.233:80
115.72.4.76:10003
68.183.143.134:80
3.123.150.192:80
216.144.236.89:3128
181.78.105.152:999
156.155.29.131:8080
103.243.238.166:31912
45.177.16.134:999
202.176.1.25:4343
89.117.130.19:80
67.43.228.250:28037
89.23.112.143:80
45.67.221.18:80
176.9.239.181:80
222.252.194.204:8080
38.7.1.185:999
109.238.180.90:8080
177.93.16.66:8080
202.179.93.132:58080
103.169.254.45:6080
190.14.251.109:999
94.68.245.147:8080
203.111.253.103:8080
202.154.18.172:8087
190.60.44.107:999
200.76.28.204:999
103.63.26.119:8080
213.169.33.7:8001
8.219.97.248:80
3.71.239.218:3128
35.76.62.196:80
72.10.160.171:16399
38.150.15.11:80
159.65.245.255:80
27.147.144.42:96
167.249.29.220:999
198.145.118.93:8080
103.167.68.35:8080
185.255.88.18:9090
82.213.29.203:18000
103.169.131.46:8080
177.53.155.204:999
180.94.80.18:8080
173.208.246.194:40000
154.65.39.7:80
167.99.124.118:80
13.55.210.141:3128
54.152.3.36:80
91.107.182.7:1080
51.195.248.19:80
34.246.112.243:80
154.208.58.89:8080
204.199.68.201:53281
"""

    proxy_list = load_proxies_from_text(proxy_text)

    # Filter out obviously invalid proxies like 0.0.0.0 and 127.0.0.7
    proxy_list = [p for p in proxy_list if not p.startswith(('0.0.0.0', '127.0.0'))]

    print(f"Loaded {len(proxy_list)} proxies to test")

    # Test the proxy list
    results_df = test_proxy_list(proxy_list, concurrent=True, max_workers=10)

    # Save results to CSV
    results_df.to_csv("proxy_test_results.csv", index=False)

    # Get working proxies for Google Trends test
    working_proxies = results_df[results_df['working'] == True]['proxy'].tolist()

    if working_proxies:
        print("\nWorking Proxies:")
        for proxy in working_proxies:
            print(proxy)

        # Test Google Trends access with working proxies
        trends_results = test_google_trends_access(working_proxies)
        trends_results.to_csv("google_trends_access_results.csv", index=False)

        # Print Google Trends-compatible proxies
        trends_compatible = trends_results[trends_results['google_trends_access'] == True]['proxy'].tolist()

        if trends_compatible:
            print("\nProxies compatible with Google Trends:")
            for proxy in trends_compatible:
                print(proxy)
            print(f"\nTotal Google Trends-compatible proxies: {len(trends_compatible)}/{len(working_proxies)}")
    else:
        print("No working proxies found to test Google Trends access.")


if __name__ == "__main__":
    main()