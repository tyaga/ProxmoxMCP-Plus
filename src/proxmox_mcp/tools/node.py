"""
Node-related tools for Proxmox MCP.

This module provides tools for managing and monitoring Proxmox nodes:
- Listing all nodes in the cluster with their status
- Getting detailed node information including:
  * CPU usage and configuration
  * Memory utilization
  * Uptime statistics
  * Health status

The tools handle both basic and detailed node information retrieval,
with fallback mechanisms for partial data availability.
"""
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from mcp.types import TextContent as Content
from proxmox_mcp.tools.base import ProxmoxTool

class NodeTools(ProxmoxTool):
    """Tools for managing Proxmox nodes.
    
    Provides functionality for:
    - Retrieving cluster-wide node information
    - Getting detailed status for specific nodes
    - Monitoring node health and resources
    - Handling node-specific API operations
    
    Implements fallback mechanisms for scenarios where detailed
    node information might be temporarily unavailable.
    """

    def get_nodes(self) -> List[Content]:
        """List all nodes in the Proxmox cluster with detailed status.

        Retrieves comprehensive information for each node including:
        - Basic status (online/offline)
        - Uptime statistics
        - CPU configuration and count
        - Memory usage and capacity
        
        Implements a fallback mechanism that returns basic information
        if detailed status retrieval fails for any node.

        Returns:
            List of Content objects containing formatted node information:
            {
                "node": "node_name",
                "status": "online/offline",
                "uptime": seconds,
                "maxcpu": cpu_count,
                "memory": {
                    "used": bytes,
                    "total": bytes
                }
            }

        Raises:
            RuntimeError: If the cluster-wide node query fails
        """
        cached = self._cache_get("nodes:list")
        if cached is not None:
            return self._format_response(cached, "nodes")

        try:
            # Single call — /cluster/resources?type=node returns uptime/mem/maxmem/maxcpu
            # for all nodes without per-node round-trips.
            resources = self._call_with_retry(
                "get nodes", lambda: self.proxmox.cluster.resources.get(type="node")
            )
            node_rows = [r for r in resources if isinstance(r, dict) and r.get("node")]

            # Fetch RRD disk I/O for all online nodes in parallel.
            def _fetch_rrd(node_name: str) -> Dict:
                try:
                    samples = self.proxmox.nodes(node_name).rrddata.get(timeframe="hour")
                    return self._rrd_last_sample(samples)
                except Exception:
                    return {}

            online_names = [r["node"] for r in node_rows if r.get("status") != "offline"]
            with ThreadPoolExecutor(max_workers=len(online_names) or 1) as pool:
                rrd_map = dict(zip(online_names, pool.map(_fetch_rrd, online_names)))

            nodes = []
            for r in node_rows:
                name = r["node"]
                rrd = rrd_map.get(name, {})
                nodes.append({
                    "node": name,
                    "status": r.get("status", "unknown"),
                    "uptime": r.get("uptime", 0),
                    "maxcpu": r.get("maxcpu", "N/A"),
                    "cpu_usage": round(float(r.get("cpu", 0) or 0) * 100, 1),
                    "memory": {
                        "used": r.get("mem", 0),
                        "total": r.get("maxmem", 0),
                    },
                    "disk_io": {
                        "iowait_pct": round(float(rrd.get("iowait") or 0) * 100, 2),
                        "pressure_io_some": round(float(rrd.get("pressureiosome") or 0) * 100, 1),
                    },
                })
            self._cache_set("nodes:list", nodes, ttl_seconds=5)
            return self._format_response(nodes, "nodes")
        except Exception as e:
            self._handle_error("get nodes", e)

    def get_node_status(self, node: str) -> List[Content]:
        """Get detailed status information for a specific node."""
        try:
            # Fetch status and RRD data in parallel — 2 requests, not sequential.
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_status = pool.submit(self.proxmox.nodes(node).status.get)
                f_rrd = pool.submit(
                    self.proxmox.nodes(node).rrddata.get,
                    timeframe="hour",
                )
                raw = f_status.result()  # propagate status errors to the fallback handler
                try:
                    rrd_sample = self._rrd_last_sample(f_rrd.result())
                except Exception as rrd_err:
                    self.logger.warning("RRD data unavailable for node %s: %s", node, rrd_err)
                    rrd_sample = {}

            normalized = self._normalize_node_status(raw, online=True, rrd=rrd_sample)
            return self._format_response((node, normalized), "node_status")
        except Exception as e:
            try:
                nodes = self.proxmox.nodes.get()
            except Exception:
                self._handle_error(f"get status for node {node}", e)

            for entry in nodes:
                if entry.get("node") != node:
                    continue
                if entry.get("status") == "offline":
                    self.logger.warning(
                        "Using offline status for node %s due to status error: %s",
                        node,
                        e,
                    )
                    fallback = self._normalize_node_status({
                        "memory": {"used": entry.get("mem", 0), "total": entry.get("maxmem", 0), "free": 0},
                        "cpuinfo": {"cpus": entry.get("maxcpu", "N/A")},
                        "uptime": 0,
                    }, online=False)
                    return self._format_response((node, fallback), "node_status")
                break

            self._handle_error(f"get status for node {node}", e)

    @staticmethod
    def _rrd_last_sample(samples: Any) -> Dict:
        """Return the most recent non-null RRD sample from node rrddata."""
        if not isinstance(samples, list):
            return {}
        for s in reversed(samples):
            if isinstance(s, dict) and s.get("iowait") is not None:
                return s
        return {}

    @staticmethod
    def _normalize_node_status(raw: dict, online: bool, rrd: Optional[Dict] = None) -> dict:
        """Reshape /nodes/{node}/status response into a stable dict for the formatter."""
        cpuinfo = raw.get("cpuinfo", {}) if isinstance(raw, dict) else {}
        memory = raw.get("memory", {}) if isinstance(raw, dict) else {}
        swap = raw.get("swap", {}) if isinstance(raw, dict) else {}
        rootfs = raw.get("rootfs", {}) if isinstance(raw, dict) else {}
        loadavg = raw.get("loadavg", []) if isinstance(raw, dict) else []
        rrd = rrd or {}
        return {
            "status": "online" if online else "offline",
            "uptime": raw.get("uptime", 0),
            "cpu": {
                "usage": round(float(raw.get("cpu", 0) or 0) * 100, 1),
                "cores": cpuinfo.get("cpus", "N/A"),
                "mhz": cpuinfo.get("mhz", ""),
            },
            "memory": {
                "used": memory.get("used", 0),
                "total": memory.get("total", 0),
                "free": memory.get("free", 0),
            },
            "swap": {
                "used": swap.get("used", 0),
                "total": swap.get("total", 0),
            },
            "rootfs": {
                "used": rootfs.get("used", 0),
                "total": rootfs.get("total", 0),
            },
            "disk_io": {
                "iowait_pct": round(float(rrd.get("iowait") or 0) * 100, 2),
                "pressure_io_some": round(float(rrd.get("pressureiosome") or 0) * 100, 1),
            },
            "loadavg": loadavg,
            "kversion": raw.get("kversion", ""),
            "pveversion": raw.get("pveversion", ""),
        }
