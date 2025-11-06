def ip_to_int(ip):
    """将IP地址转换为整数，便于计算"""
    octets = list(map(int, ip.split('.')))
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

def int_to_ip(num):
    """将整数转换为IP地址"""
    return f"{(num >> 24) & 0xFF}.{(num >> 16) & 0xFF}.{(num >> 8) & 0xFF}.{num & 0xFF}"

def calculate_subnet_size(prefix_len):
    """计算网段包含的总IP数量（包括网络地址和广播地址）"""
    if prefix_len < 0 or prefix_len > 32:
        return 0
    return 2 **(32 - prefix_len)

def find_min_subnet(ips_int, min_prefix=24):
    """
    为一组IP找到最小网段（不小于min_prefix，默认24）
    返回：网段CIDR、起始IP、结束IP、前缀长度
    """
    min_ip = min(ips_int)
    max_ip = max(ips_int)

    # 计算最小前缀长度：从32位开始，找到能覆盖所有IP的最小前缀，但不小于min_prefix
    prefix_len = 32
    while prefix_len >= min_prefix:
        mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF  # 子网掩码（整数）
        network = min_ip & mask  # 网络地址（整数）
        broadcast = network | (~mask & 0xFFFFFFFF)  # 广播地址（整数）

        # 检查所有IP是否在当前网段内
        if all(network <= ip <= broadcast for ip in ips_int):
            start_ip = int_to_ip(network)
            end_ip = int_to_ip(broadcast)
            cidr = f"{start_ip}/{prefix_len}"
            return cidr, start_ip, end_ip, prefix_len
        prefix_len -= 1

    # 如果找不到满足条件的，强制使用min_prefix（如24）
    mask = (0xFFFFFFFF << (32 - min_prefix)) & 0xFFFFFFFF
    network = min_ip & mask
    broadcast = network | (~mask & 0xFFFFFFFF)
    start_ip = int_to_ip(network)
    end_ip = int_to_ip(broadcast)
    cidr = f"{start_ip}/{min_prefix}"
    return cidr, start_ip, end_ip, min_prefix

def split_subnets(ips, min_prefix=24):
    """
    拆分IP列表为网段集合（区分聚合网段和/32网段）
    返回：(聚合网段列表, /32网段列表)
    聚合网段列表元素：(cidr, start_ip, end_ip, current_ips, total_ips, ratio)
    """
    ips_int = [ip_to_int(ip) for ip in ips]
    ips_int_sorted = sorted(ips_int)
    aggregate_subnets = []  # 存储聚合网段（非/32）
    single_ips = []         # 存储/32网段的IP

    while ips_int_sorted:
        current_ip = ips_int_sorted[0]
        current_group = [current_ip]

        # 提取当前IP的前24位（判断是否同属一个/24网段）
        current_24 = current_ip & 0xFFFFFF00  # 24位掩码对应的网络地址

        # 尝试添加同属一个/24网段的IP
        for ip in ips_int_sorted[1:]:
            if (ip & 0xFFFFFF00) == current_24:  # 同属一个/24网段
                current_group.append(ip)
            else:
                break  # 不同/24网段，停止添加

        # 区分聚合网段和单个IP
        if len(current_group) == 1:
            # 单个IP，加入/32列表
            single_ip = int_to_ip(current_ip)
            single_ips.append(single_ip)
        else:
            # 多个IP，进行聚合
            cidr, start_ip, end_ip, prefix_len = find_min_subnet(current_group, min_prefix)
            current_ips = [int_to_ip(ip) for ip in current_group]
            total_ips = calculate_subnet_size(prefix_len)
            ratio = len(current_ips) / total_ips * 100  # 计算占比（百分比）
            aggregate_subnets.append((cidr, start_ip, end_ip, current_ips, total_ips, ratio))

        # 从列表中移除已处理的IP
        ips_int_sorted = [ip for ip in ips_int_sorted if ip not in current_group]

    return aggregate_subnets, single_ips

def read_ips_from_file(file_path):
    """从文件读取IP地址，忽略空行和注释行（#开头）"""
    ips = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            ips.append(line)
    return ips

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("使用方法：python breakIP.py <IP文件路径>")
        print("示例：python breakIP.py ip.txt")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        ip_list = read_ips_from_file(file_path)
        if not ip_list:
            print("文件中未找到有效的IP地址")
            sys.exit(1)
    except FileNotFoundError:
        print(f"错误：找不到文件 '{file_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件时发生错误：{str(e)}")
        sys.exit(1)

    # 执行网段划分（区分聚合网段和/32网段）
    aggregate_subnets, single_ips = split_subnets(ip_list, min_prefix=24)

    # 输出结果
    print("IP地址网段划分结果：")
    print("="*80)

    # 先输出聚合网段（非/32）
    if aggregate_subnets:
        print("一、聚合网段（最小/24）：")
        for i, (cidr, start_ip, end_ip, ips, total_ips, ratio) in enumerate(aggregate_subnets, 1):
            print(f"\n网段{i}：{cidr}")
            print(f"  网段范围：{start_ip} - {end_ip}")
            #print(f"  网段总IP数：{total_ips}")
            #print(f"  实际包含IP数：{len(ips)}")
            print(f"  网段内占比：{ratio:.6f}%")  # 保留6位小数
            print("  包含IP：")
            for ip in ips:
                print(f"    - {ip}")
        print("\n" + "-"*80)

    # 最后输出/32网段的IP
    if single_ips:
        print("二、独立IP（/32网段）：")
        total_32 = len(single_ips)
        print(f"  共{total_32}个独立IP（每个网段仅包含1个IP，占比100%）：")
        for i, ip in enumerate(single_ips, 1):
            print(f"{ip}")
        print("-"*80)

    if not aggregate_subnets and not single_ips:
        print("未找到可划分的IP地址")
