"""
Output templates for Proxmox MCP resource types.
"""
from typing import Dict, List, Any
from proxmox_mcp.formatting.formatters import ProxmoxFormatters
from proxmox_mcp.formatting.theme import ProxmoxTheme

class ProxmoxTemplates:
    """Output templates for different Proxmox resource types."""
    
    @staticmethod
    def node_list(nodes: List[Dict[str, Any]]) -> str:
        """Template for node list output.
        
        Args:
            nodes: List of node data dictionaries
            
        Returns:
            Formatted node list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['node']} Proxmox Nodes"]
        
        for node in nodes:
            status = node.get("status", "unknown")
            memory = node.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            cpu_usage = node.get("cpu_usage", 0)

            result.extend([
                "",
                f"{ProxmoxTheme.RESOURCES['node']} {node['node']}",
                f"  - Status: {status.upper()}",
                f"  - Uptime: {ProxmoxFormatters.format_uptime(node.get('uptime', 0))}",
                f"  - CPU: {cpu_usage:.1f}%  ({node.get('maxcpu', 'N/A')} cores)",
                f"  - Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)",
            ])

            disk_io = node.get("disk_io")
            if disk_io is not None:
                iowait = disk_io.get("iowait_pct", 0)
                pressure = disk_io.get("pressure_io_some", 0)
                parts = [f"{iowait:.2f}% iowait"]
                if pressure:
                    parts.append(f"{pressure:.1f}% io pressure")
                result.append(f"  - Disk I/O: {',  '.join(parts)}")

        return "\n".join(result)
    
    @staticmethod
    def node_status(node: str, status: Dict[str, Any]) -> str:
        """Template for detailed node status output."""
        cpu = status.get("cpu", {})
        cpu_usage = cpu.get("usage", 0)
        cpu_cores = cpu.get("cores", "N/A")
        cpu_mhz = cpu.get("mhz", "")

        memory = status.get("memory", {})
        memory_used = memory.get("used", 0)
        memory_total = memory.get("total", 0)
        memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0

        result = [
            f"{ProxmoxTheme.RESOURCES['node']} Node: {node}",
            f"  - Status: {status.get('status', 'unknown').upper()}",
            f"  - Uptime: {ProxmoxFormatters.format_uptime(status.get('uptime', 0))}",
            f"  - CPU: {cpu_usage:.1f}%  ({cpu_cores} cores"
            + (f", {cpu_mhz} MHz" if cpu_mhz else "") + ")",
            f"  - Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
            f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)",
        ]

        swap = status.get("swap", {})
        swap_used = swap.get("used", 0)
        swap_total = swap.get("total", 0)
        if swap_total > 0:
            swap_percent = swap_used / swap_total * 100
            result.append(
                f"  - Swap: {ProxmoxFormatters.format_bytes(swap_used)} / "
                f"{ProxmoxFormatters.format_bytes(swap_total)} ({swap_percent:.1f}%)"
            )

        rootfs = status.get("rootfs", {})
        rootfs_used = rootfs.get("used", 0)
        rootfs_total = rootfs.get("total", 0)
        if rootfs_total > 0:
            rootfs_percent = rootfs_used / rootfs_total * 100
            result.append(
                f"  - Root disk: {ProxmoxFormatters.format_bytes(rootfs_used)} / "
                f"{ProxmoxFormatters.format_bytes(rootfs_total)} ({rootfs_percent:.1f}%)"
            )

        disk_io = status.get("disk_io")
        if disk_io is not None:
            iowait = disk_io.get("iowait_pct", 0)
            pressure = disk_io.get("pressure_io_some", 0)
            parts = [f"{iowait:.2f}% iowait"]
            if pressure:
                parts.append(f"{pressure:.1f}% io pressure")
            result.append(f"  - Disk I/O: {',  '.join(parts)}")

        loadavg = status.get("loadavg", [])
        if loadavg:
            result.append(f"  - Load avg: {' / '.join(str(x) for x in loadavg[:3])}")

        pveversion = status.get("pveversion", "")
        if pveversion:
            result.append(f"  - PVE version: {pveversion}")

        return "\n".join(result)
    
    @staticmethod
    def vm_list(vms: List[Dict[str, Any]]) -> str:
        """Template for VM list output.
        
        Args:
            vms: List of VM data dictionaries
            
        Returns:
            Formatted VM list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['vm']} Virtual Machines"]
        
        for vm in vms:
            memory = vm.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            result.extend([
                "",  # Empty line between VMs
                f"{ProxmoxTheme.RESOURCES['vm']} {vm['name']} (ID: {vm['vmid']})",
                f"  - Status: {vm['status'].upper()}",
                f"  - Node: {vm['node']}",
                f"  - CPU Cores: {vm.get('cpus', 'N/A')}",
                f"  - Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
            ])
            
        return "\n".join(result)
    
    @staticmethod
    def storage_list(storage: List[Dict[str, Any]]) -> str:
        """Template for storage list output.
        
        Args:
            storage: List of storage data dictionaries
            
        Returns:
            Formatted storage list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['storage']} Storage Pools"]
        
        for store in storage:
            used = store.get("used", 0)
            total = store.get("total", 0)
            percent = (used / total * 100) if total > 0 else 0
            
            result.extend([
                "",  # Empty line between storage pools
                f"{ProxmoxTheme.RESOURCES['storage']} {store['storage']}",
                f"  - Status: {store.get('status', 'unknown').upper()}",
                f"  - Type: {store['type']}",
                f"  - Usage: {ProxmoxFormatters.format_bytes(used)} / "
                f"{ProxmoxFormatters.format_bytes(total)} ({percent:.1f}%)"
            ])
            
        return "\n".join(result)
    
    @staticmethod
    def container_list(containers: List[Dict[str, Any]]) -> str:
        """Template for container list output.
        
        Args:
            containers: List of container data dictionaries
            
        Returns:
            Formatted container list string
        """
        if not containers:
            return f"{ProxmoxTheme.RESOURCES['container']} No containers found"
            
        result = [f"{ProxmoxTheme.RESOURCES['container']} Containers"]
        
        for container in containers:
            memory = container.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            result.extend([
                "",  # Empty line between containers
                f"{ProxmoxTheme.RESOURCES['container']} {container['name']} (ID: {container['vmid']})",
                f"  - Status: {container['status'].upper()}",
                f"  - Node: {container['node']}",
                f"  - CPU Cores: {container.get('cpus', 'N/A')}",
                f"  - Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
            ])
            
        return "\n".join(result)

    @staticmethod
    def cluster_status(status: Dict[str, Any]) -> str:
        """Template for cluster status output.
        
        Args:
            status: Cluster status data
            
        Returns:
            Formatted cluster status string
        """
        result = [f"{ProxmoxTheme.SECTIONS['configuration']} Proxmox Cluster"]
        
        # Basic cluster info
        result.extend([
            "",
            f"  - Name: {status.get('name', 'N/A')}",
            f"  - Quorum: {'OK' if status.get('quorum') else 'NOT OK'}",
            f"  - Nodes: {status.get('nodes', 0)}",
        ])
        
        # Add resource count if available
        resources = status.get('resources', [])
        if resources:
            result.append(f"  - Resources: {len(resources)}")
        
        return "\n".join(result)
