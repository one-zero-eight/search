import torch

print(torch.cuda.is_available())  # должно вывести True
print(torch.cuda.device_count())  # число доступных GPU
