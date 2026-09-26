import torch
import time

print("PyTorch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0))

device = torch.device("cuda")

x = torch.randn(5000, 5000, device=device)
y = torch.randn(5000, 5000, device=device)

torch.cuda.synchronize()

start = time.time()

z = torch.matmul(x, y)

torch.cuda.synchronize()

end = time.time()

print("Matrix multiplication completed")
print("Time:", end - start, "seconds")
print("Result device:", z.device)