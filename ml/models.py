#!/usr/bin/env python
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import TransformerEncoder, TransformerEncoderLayer
from cfg import context_length, input_length as inst_length
from enet import E1DNet
from vit import InsT

class Fusion1dFC(nn.Module):
    def __init__(self, out):
        super(Fusion1dFC, self).__init__()
        self.out = out
        self._fu0 = nn.Linear(inst_length, out, bias=False)
        #self._fu1 = nn.Linear(inst_length, out, bias=False)
        self._conv = nn.Conv1d(in_channels=inst_length,
                               out_channels=out,
                               kernel_size=1, bias=False)

    def forward(self, x):
        x = x.view(-1, context_length, inst_length)
        x0 = self._fu0(x[:, 0, :])
        x0 = x0.view(-1, self.out, 1)
        x0 = x0.expand(-1, -1, context_length - 1)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = self._conv(x[:, :, 1:context_length])
        x += x0
        #y = x.new(x.size(0), self.out, context_length - 1)
        ##print(y.size())
        #for i in range(1, context_length):
        #    y[:, :, i-1] = self._fu1(x[:, i, :]) + x0
        #x = F.relu(y)
        x = F.relu(x)
        return x

class Fusion1d(nn.Module):
    def __init__(self, out):
        super(Fusion1d, self).__init__()
        self._conv = nn.Conv1d(in_channels=inst_length*2, out_channels=out, kernel_size=1, bias=False)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        #copies = x[:,:,0].unsqueeze(-1)
        copies = x[:,:,0:1]
        #copies = copies.repeat(1, 1, context_length - 1)
        copies = copies.expand(-1, -1, context_length - 1)
        #test = torch.cat((x,copies),-2)
        x = torch.cat((x[:,:,1:context_length],copies),1)
        #print(x.size())
        x = self._conv(x)
        x = F.relu(x)
        return x

class Fusion1dS(nn.Module):
    def __init__(self, out):
        super(Fusion1dS, self).__init__()
        self._conv = nn.Conv1d(in_channels=inst_length*2, out_channels=out, kernel_size=1, bias=False)
        self._cxt_size = context_length

    def forward(self, x):
        copies = x[:,:,0:1]
        copies = copies.expand(-1, -1, self._cxt_size - 1)
        x = torch.cat((x[:,:,1:self._cxt_size],copies),1)
        x = self._conv(x)
        return x

class FC2(nn.Module):
    def __init__(self, out, f1):
        super(FC2, self).__init__()
        self.fc1 = nn.Linear(inst_length*context_length, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        x = x.view(-1, inst_length*context_length)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class FC3(nn.Module):
    def __init__(self, out, f1, f2):
        super(FC3, self).__init__()
        self.fc1 = nn.Linear(inst_length*context_length, f1)
        self.fc2 = nn.Linear(f1, f2)
        self.fc3 = nn.Linear(f2, out)

    def forward(self, x):
        x = x.view(-1, inst_length*context_length)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class CNN_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, f1):
        super(CNN_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input *= ch1
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3(nn.Module):
    def __init__(self, out, ck1, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN3, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.f1_input = ch3 * (context_length - ck1 - ck2 - ck3 + 3)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN2_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, f1):
        super(CNN2_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input *= ch2
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN2_P(nn.Module):
    def __init__(self, out, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN2_P, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=2)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.f1_input = ch3 * (context_length - 1 - ck2 - ck3 + 2)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.conv1(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.conv1(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_P(nn.Module):
    def __init__(self, out, pc, ck1, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN3_P, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.f1_input = ch3 * (context_length - 1 - ck1 - ck2 - ck3 + 3)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_F_P(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F_P, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length - 1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_F_PP(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F_PP, self).__init__()
        self._fu = Fusion1d(pc)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length - 1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        x = self._fu(x)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_F_P_BN(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F_P_BN, self).__init__()
        self._fu = Fusion1dS(pc)
        self._bn_fu = nn.BatchNorm1d(num_features=pc)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length - 1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self._bn_fu(self._fu(x)))
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_F_P_COM(nn.Module):
    def __init__(self, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F_P_COM, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length - 1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, 22)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        fc = torch.argmax(x[:, 2:12], dim=1)
        rc = torch.argmax(x[:, 12:22], dim=1)
        return x, fc, rc

class CNN3_F_P2(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(CNN3_F_P2, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.convp2 = nn.Linear(pc, pc)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length - 1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        y = torch.unsqueeze(self.convp2(F.relu(torch.squeeze(y, -1))), -1)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            xo = torch.unsqueeze(self.convp2(F.relu(torch.squeeze(xo, -1))), -1)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN5(nn.Module):
    def __init__(self, out, ck1, ch1, ck2, ch2, ck3, ch3, ck4, ch4, ck5, ch5, f1):
        super(CNN5, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5)
        self.f1_input = ch5 * (context_length - ck1 - ck2 - ck3 - ck4 - ck5 + 5)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN7_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, ck6, ch6, cs6, cp6, ck7, ch7, cs7, cp7, f1):
        super(CNN7_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.conv6 = nn.Conv1d(in_channels=ch5, out_channels=ch6, kernel_size=ck6, stride=cs6, padding=cp6)
        self.conv7 = nn.Conv1d(in_channels=ch6, out_channels=ch7, kernel_size=ck7, stride=cs7, padding=cp7)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp6 - ck6) / cs6 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp7 - ck7) / cs7 + 1)
        print(self.f1_input)
        self.f1_input *= ch7
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = F.relu(self.conv6(x))
        x = F.relu(self.conv7(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN7_BN(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, ck6, ch6, cs6, cp6, ck7, ch7, cs7, cp7, f1):
        super(CNN7_BN, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self._bn_fu = nn.BatchNorm1d(num_features=ch1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.conv6 = nn.Conv1d(in_channels=ch5, out_channels=ch6, kernel_size=ck6, stride=cs6, padding=cp6)
        self.conv7 = nn.Conv1d(in_channels=ch6, out_channels=ch7, kernel_size=ck7, stride=cs7, padding=cp7)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp6 - ck6) / cs6 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp7 - ck7) / cs7 + 1)
        print(self.f1_input)
        self.f1_input *= ch7
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self._bn_fu(self.conv1(x)))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = F.relu(self.conv6(x))
        x = F.relu(self.conv7(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN7_F_P(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, ck6, ch6, cs6, cp6, ck7, ch7, cs7, cp7, f1):
        super(CNN7_F_P, self).__init__()
        self._fu = Fusion1dS(pc)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.conv6 = nn.Conv1d(in_channels=ch5, out_channels=ch6, kernel_size=ck6, stride=cs6, padding=cp6)
        self.conv7 = nn.Conv1d(in_channels=ch6, out_channels=ch7, kernel_size=ck7, stride=cs7, padding=cp7)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp6 - ck6) / cs6 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp7 - ck7) / cs7 + 1)
        print(self.f1_input)
        self.f1_input *= ch7
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self._fu(x))
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = F.relu(self.conv6(x))
        x = F.relu(self.conv7(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN5_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, f1):
        super(CNN5_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input)
        self.f1_input *= ch5
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN4_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, f1):
        super(CNN4_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input *= ch4
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_P2(nn.Module):
    def __init__(self, out, pc, ck1, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN3_P2, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.convp2 = nn.Linear(pc, pc)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.f1_input = ch3 * (context_length - 1 - ck1 - ck2 - ck3 + 3)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        y = torch.unsqueeze(self.convp2(F.relu(torch.squeeze(y, -1))), -1)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            xo = torch.unsqueeze(self.convp2(F.relu(torch.squeeze(xo, -1))), -1)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_P_lat(nn.Module):
    def __init__(self, out, pc, ck1, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN3_P_lat, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.c3_output = ch3 * (context_length - 1 - ck1 - ck2 - ck3 + 3)
        self.f1_input = self.c3_output + context_length * inst_length
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        xin = x;
        #xin = xin.view(-1, inst_length * context_length)
        xin = x.view(-1, context_length, inst_length).transpose(2,1)
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.c3_output)
        x = torch.cat((x, xin), 1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN3_FPB(nn.Module):
    def __init__(self, out, pc, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, bch1, bch2, bch3, f1):
        super(CNN3_FPB, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.c3_output = math.floor((context_length -1 + 2 * cp1 - ck1) / cs1 + 1)
        print(self.c3_output)
        self.c3_output = math.floor((self.c3_output + 2 * cp2 - ck2) / cs2 + 1)
        print(self.c3_output)
        self.c3_output = math.floor((self.c3_output + 2 * cp3 - ck3) / cs3 + 1)
        print(self.c3_output)
        self.c3_output *= ch3
        self.c3_output = int(self.c3_output)
        self.bconv1 = nn.Conv1d(in_channels=inst_length, out_channels=bch1, kernel_size=1)
        self.bconv2 = nn.Conv1d(in_channels=bch1, out_channels=bch2, kernel_size=1)
        self.bconv3 = nn.Conv1d(in_channels=bch2, out_channels=bch3, kernel_size=1)
        self.bc3_output = bch3
        self.f1_input = self.c3_output + self.bc3_output
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        first = x[:, :, 0:1]
        first = F.relu(self.bconv1(first))
        first = F.relu(self.bconv2(first))
        first = F.relu(self.bconv3(first))
        first = first.view(-1, self.bc3_output)
        x = F.relu(y)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.c3_output)
        x = torch.cat((x, first), 1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class CNN3_P_D_C(nn.Module):
    def __init__(self, out, pc, ck1, ch1, ck2, ch2, ck3, ch3, f1):
        super(CNN3_P_D_C, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length,    # e.g. 33                   
                               out_channels=pc,  # e.g. 64                             
                               kernel_size=2)
        self.conv1 = nn.Conv1d(in_channels=pc, out_channels=ch1, kernel_size=ck1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3)
        self.f1_input = ch3 * (context_length  - ck1 - ck2 - ck3 + 3)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

        self.convt = nn.Conv1d(in_channels=inst_length*2,
                               out_channels=pc,
                               kernel_size=1)

        self.convd = nn.Conv1d(in_channels = pc,
                               out_channels = pc,
                               kernel_size = 1)

        self.newlin = nn.Linear(pc,pc)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)

        copies = x[:,:,0].unsqueeze(-1)
        copies=copies.repeat(1,1, context_length)
        test  = torch.cat((x,copies),-2)

        y = self.convt(test)
        y = F.tanh(y) # F.relu(y)
        y = self.convd(y)
        y = F.tanh(y) #F.relu(y)

        x = F.relu(self.conv1(y))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class FC2_P(nn.Module):
    def __init__(self, out, pc, f1):
        super(FC2_P, self).__init__()
        self.convp = nn.Conv1d(in_channels=inst_length, out_channels=pc, kernel_size=2)
        self.f1_input = pc * (context_length - 1)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        xi = torch.cat((x[:, :, 0:1], x[:, :, 1:2]), 2)
        y = self.convp(xi)
        for i in range(2, context_length):
            xi = torch.cat((x[:, :, 0:1], x[:, :, i:i+1]), 2)
            xo = self.convp(xi)
            y = torch.cat((y, xo), 2)
        x = F.relu(y)
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNN8_F(nn.Module):
    def __init__(self, out, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, ck6, ch6, cs6, cp6, ck7, ch7, cs7, cp7, ck8, ch8, cs8, cp8, f1):
        super(CNN8_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.conv6 = nn.Conv1d(in_channels=ch5, out_channels=ch6, kernel_size=ck6, stride=cs6, padding=cp6)
        self.conv7 = nn.Conv1d(in_channels=ch6, out_channels=ch7, kernel_size=ck7, stride=cs7, padding=cp7)
        self.conv8 = nn.Conv1d(in_channels=ch7, out_channels=ch8, kernel_size=ck8, stride=cs8, padding=cp8)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp6 - ck6) / cs6 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp7 - ck7) / cs7 + 1)
        print(self.f1_input, end=' ')
        self.f1_input = math.floor((self.f1_input + 2 * cp8 - ck8) / cs8 + 1)
        print(self.f1_input)
        self.f1_input *= ch8
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = F.relu(self.conv6(x))
        x = F.relu(self.conv7(x))
        x = F.relu(self.conv8(x))
        x = x.view(-1, self.f1_input)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

######################################################################
# ``PositionalEncoding`` module injects some information about the
# relative or absolute position of the tokens in the sequence. The
# positional encodings have the same dimension as the embeddings so that
# the two can be summed. Here, we use ``sine`` and ``cosine`` functions of
# different frequencies.
#

class PositionalEncoding(nn.Module):

    def __init__(self, d_model, dropout=0.1, max_len=500):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0)/d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:context_length, :]
        return self.dropout(x)


class CustomTransformerModel(nn.Module):

    def __init__(self,
                 ninp, # what dimension our input is
                 nhead, # number of 'heads'
                 nhid,  # dimension of the feedforward network in nn.TransformerEncoder
                 nlayers, #number of encoder layers
                 nout,
                 dropout=0.5):
        super(CustomTransformerModel, self).__init__()

        self.model_type = 'Transformer'
        #self.src_mask = None
        self.pos_encoder = PositionalEncoding(ninp, dropout)
        encoder_layers = TransformerEncoderLayer(d_model=ninp,
                                                 nhead=nhead,
                                                 dim_feedforward=nhid,
                                                 dropout=dropout)
        self.transformer_encoder = TransformerEncoder(encoder_layers, nlayers)

        self.ninp = ninp
        self.decoder = nn.Linear(ninp, nout)
        src_mask = self._generate_square_subsequent_mask(111)
        self.register_buffer('src_mask', src_mask)
        self.init_weights()

    def _generate_square_subsequent_mask(self, sz):
        mask = (torch.triu(torch.ones(sz, sz)) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float(0.0)).masked_fill(mask == 1, float(0.0))
        return mask
    
    def init_weights(self):
        initrange = 0.1

        self.decoder.bias.data.zero_()
        self.decoder.weight.data.uniform_(-initrange, initrange)

    def forward(self, src):
        src = src.view(-1, context_length, inst_length) #.transpose(2,1)
        src = src.transpose(0,1) # for multigpu

        src = src * math.sqrt(self.ninp)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src, self.src_mask)
        output = self.decoder(output)

        return output[-1]


class LLDTransformerModel(nn.Module):
    def __init__(self,
                 nout,
                 ninp,
                 nhead, # number of 'heads'
                 nhid,  # dimension of the feedforward network in nn.TransformerEncoder
                 nlayers, #number of encoder layers
                 dropout=0.1):
        super(LLDTransformerModel, self).__init__()

        self.model_type = 'Transformer'
        self._conv_stem = nn.Conv1d(inst_length, ninp, kernel_size=1, stride=1, bias=False)
        self.pos_encoder = PositionalEncoding(ninp, dropout)
        encoder_layers = TransformerEncoderLayer(d_model=ninp,
                                                 nhead=nhead,
                                                 dim_feedforward=nhid,
                                                 dropout=dropout)
        self.encoder = TransformerEncoder(encoder_layers, nlayers)

        self.decoder = nn.Linear(ninp, nout)
        src_mask = self.generate_square_subsequent_mask(context_length)
        self.register_buffer('src_mask', src_mask)
        self.init_weights()

    def generate_square_subsequent_mask(self, sz):
        mask = (torch.triu(torch.ones(sz, sz)) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float('-inf')).masked_fill(mask == 1, float(0.0))
        return mask

    def init_weights(self):
        initrange = 0.1
        self.decoder.bias.data.zero_()
        self.decoder.weight.data.uniform_(-initrange, initrange)

    def forward(self, src):
        src = src.view(-1, context_length, inst_length)
        src = torch.flip(src, [1])
        src = src.transpose(1,2)
        src = F.relu(self._conv_stem(src))
        src = src.transpose(1,2)
        src = src.transpose(0,1)

        src = self.pos_encoder(src)
        output = self.encoder(src, self.src_mask)
        output = self.decoder(output)

        return output[-1]


class InsLSTM(nn.Module):
    def __init__(self, nout, nembed, nhidden, nlayers):
        super(InsLSTM, self).__init__()

        if nembed != inst_length:
            self.inst_embed = nn.Linear(inst_length, nembed)
            #self.inst_embed = nn.Sequential(
            #    nn.Linear(inst_length, nembed)
            #    F.relu(),
            #)
        else:
            self.inst_embed = nn.Identity()
        self.lstm = nn.LSTM(nembed, nhidden, nlayers)
        self.linear = nn.Linear(nhidden, nout)

    def init_hidden(self):
        # type: () -> Tuple[nn.Parameter, nn.Parameter]
        return (
            nn.Parameter(torch.zeros(1, 1, nhidden, requires_grad=True)),
            nn.Parameter(torch.zeros(1, 1, nhidden, requires_grad=True)),
        )

    def forward(self, src):
        # reverse input order?
        src = src.view(-1, context_length, inst_length)
        src = torch.flip(src, [1])
        x = self.inst_embed(src)
        x = x.transpose(0, 1)
        x, _ = self.lstm(x)
        x = self.linear(x[-1])
        return x


class PARA_CNN3_F(nn.Module):
    def __init__(self, out, p, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, f1):
        super(PARA_CNN3_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input *= ch3
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input + p, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x, para):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(-1, self.f1_input)
        x = torch.cat((x, para), 1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class PARA_CNN7_F(nn.Module):
    def __init__(self, out, p, ck1, ch1, cs1, cp1, ck2, ch2, cs2, cp2, ck3, ch3, cs3, cp3, ck4, ch4, cs4, cp4, ck5, ch5, cs5, cp5, ck6, ch6, cs6, cp6, ck7, ch7, cs7, cp7, f1):
        super(PARA_CNN7_F, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=inst_length, out_channels=ch1, kernel_size=ck1, stride=cs1, padding=cp1)
        self.conv2 = nn.Conv1d(in_channels=ch1, out_channels=ch2, kernel_size=ck2, stride=cs2, padding=cp2)
        self.conv3 = nn.Conv1d(in_channels=ch2, out_channels=ch3, kernel_size=ck3, stride=cs3, padding=cp3)
        self.conv4 = nn.Conv1d(in_channels=ch3, out_channels=ch4, kernel_size=ck4, stride=cs4, padding=cp4)
        self.conv5 = nn.Conv1d(in_channels=ch4, out_channels=ch5, kernel_size=ck5, stride=cs5, padding=cp5)
        self.conv6 = nn.Conv1d(in_channels=ch5, out_channels=ch6, kernel_size=ck6, stride=cs6, padding=cp6)
        self.conv7 = nn.Conv1d(in_channels=ch6, out_channels=ch7, kernel_size=ck7, stride=cs7, padding=cp7)
        self.f1_input = math.floor((context_length + 2 * cp1 - ck1) / cs1 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp2 - ck2) / cs2 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp3 - ck3) / cs3 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp4 - ck4) / cs4 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp5 - ck5) / cs5 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp6 - ck6) / cs6 + 1)
        print(self.f1_input)
        self.f1_input = math.floor((self.f1_input + 2 * cp7 - ck7) / cs7 + 1)
        print(self.f1_input)
        self.f1_input *= ch7
        self.f1_input = int(self.f1_input)
        self.fc1 = nn.Linear(self.f1_input + p, f1)
        self.fc2 = nn.Linear(f1, out)

    def forward(self, x, para):
        #x = x.view(-1, inst_length, context_length)
        x = x.view(-1, context_length, inst_length).transpose(2,1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = F.relu(self.conv5(x))
        x = F.relu(self.conv6(x))
        x = F.relu(self.conv7(x))
        x = x.view(-1, self.f1_input)
        x = torch.cat((x, para), 1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x
