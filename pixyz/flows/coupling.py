import math
import torch
from torch import nn
from torch.nn import functional as F
from ..flows import Flow


class AffineCouplingFlow(Flow):
    """
    Affine coupling flow (coupling layer)

    .. math::
        f(x) = x + u h( w^T x + b)

    """

    def __init__(self, in_features):
        super().__init__(in_features)

        self.mask_type = mask_type

        self.w = nn.Parameter(torch.Tensor(1, in_features))
        self.b = nn.Parameter(torch.Tensor(1))
        self.u = nn.Parameter(torch.Tensor(1, in_features))

        self.reset_parameters()

    def deriv_tanh(self, x):
        return 1 - torch.tanh(x) ** 2

    def reset_parameters(self):
        std = 1. / math.sqrt(self.w.size(1))

        self.w.data.uniform_(-std, std)
        self.b.data.uniform_(-std, std)
        self.u.data.uniform_(-std, std)

    def forward(self, x, compute_jacobian=True):
        # modify :attr:`u` so that this flow can be invertible.
        wu = torch.mm(self.w, self.u.t())  # (1, 1)
        m_wu = -1. + F.softplus(wu)
        w_normalized = self.w / torch.norm(self.w, keepdim=True)
        u_hat = self.u + ((m_wu - wu) * w_normalized)  # (1, in_features)

        # compute the flow transformation
        linear_output = F.linear(x, self.w, self.b)  # (n_batch, 1)
        z = x + u_hat * torch.tanh(linear_output)

        if compute_jacobian:
            # compute the log-det Jacobian (logdet|dz/dx|)
            psi = self.deriv_tanh(linear_output) * self.w  # (n_batch, in_features)
            det_jacobian = 1. + torch.mm(psi, u_hat.t()).squeeze()  # (n_batch, 1) -> (n_batch)
            logdet_jacobian = torch.log(torch.abs(det_jacobian) + epsilon)
            self._logdet_jacobian = logdet_jacobian

        return z

    def extra_repr(self):
        return 'in_features={}, w=, b={}, u={}'.format(
            self.in_features, self.w, self.b, self.u
        )


def isnan(x):
    return torch.sum(x == x).cpu().numpy() == 0