import multiprocessing
import time
import psutil
from sandbox_runner import sandbox_contract_runner

TIMEOUT = 2.0
MEMORY_LIMIT_MB = 50

class SecureContractExecutor:
    def __init__(self, code: str):
        self.code = code

    def run(self, func_name: str, *args):
        manager = multiprocessing.Manager()
        return_dict = manager.dict()

        process = multiprocessing.Process(
            target=sandbox_contract_runner,
            args=(self.code, func_name, args, return_dict)
        )

        process.start()
        start_time = time.time()
        proc = psutil.Process(process.pid)

        while process.is_alive():
            elapsed = time.time() - start_time

            if elapsed > TIMEOUT:
                process.terminate()
                return {
                    "success": False,
                    "error": "Execution timeout",
                    "result": None,
                    "gas_used": 0
                }

            try:
                mem_usage_mb = proc.memory_info().rss / (1024 * 1024)
                if mem_usage_mb > MEMORY_LIMIT_MB:
                    process.terminate()
                    return {
                        "success": False,
                        "error": f"Memory limit exceeded ({int(mem_usage_mb)} MB)",
                        "result": None,
                        "gas_used": 0
                    }
            except psutil.NoSuchProcess:
                break

            time.sleep(0.05)

        process.join()

        return {
            "success": return_dict.get("error") is None,
            "error": return_dict.get("error"),
            "result": return_dict.get("result"),
            "gas_used": return_dict.get("gas_used")
        }
