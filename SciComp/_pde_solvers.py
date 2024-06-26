import numpy as np
import scipy.sparse as sp

import os
import sys

current_file_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_file_directory, ".."))

from scipy.integrate import solve_ivp
from SciComp._ode_solvers import rk4_step, heun_step, euler_step


def scipy_solver(bvp, t):
    """
    Function to solve the PDE using Scipy's solve_ivp.

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.

    Returns
    -------
    u : numpy.ndarray
        Solution to the PDE.
    """
    A, b, x_array = bvp.construct_matrix()
    
    u_boundary = bvp.f_fun(x_array, t[0])

    if bvp.q_fun is None:
        def PDE(t, u, D, A, b):
            return bvp.C * (A @ u + b)
    else:
        def PDE(t, u, D, A, b):
            return bvp.C * (A @ u + b) + bvp.q_fun(x_array, u)  

    sol = solve_ivp(PDE, (t[0], t[-1]), u_boundary, method='RK45', t_eval=t, args=(bvp.D, A, b))

    u = sol.y

    return u


def explicit_euler(bvp, t):
    """
    Function to solve the PDE using the explicit Euler method.

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.

    Returns
    -------
    solution : numpy.ndarray
        Solution to the PDE.
    """
    A, b, x_array = bvp.construct_matrix()

    u = np.zeros((len(x_array), len(t)))
    u[:, 0] = bvp.f_fun(x_array, t[0])
    u[0, :] = bvp.alpha
    u[-1, :] = bvp.beta

    # Loop over time
    for ti in range(0, len(t)-1):
        for xi in range(1, len(x_array)-1):
            if xi == 0:
                # u[0, ti+1] = u[0, ti] + bvp.C * (bvp.alpha - 2 * u[0, ti] + u[1, ti])
                u[xi, ti+1] = bvp.alpha
            elif xi > 0 and xi < bvp.N:
                u[xi, ti+1] = u[xi, ti] + bvp.C * (u[xi-1, ti] - 2 * u[xi, ti] + u[xi+1, ti])
            else:
                u[xi, ti+1] = u[xi, ti] + bvp.C * (bvp.beta - 2 * u[xi, ti] + u[xi-1, ti])

    return 


def explicit_method(bvp, t, method):
    """
    Function to solve the PDE using the explicit methods. It uses centered finite differences to
    convert the PDE into an ODE. Using the method of lines, the ODE is solved using a step function
    from _ode_solvers.py

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.
    method : str
        Method used for stepping through method of lines ODE.
        

    Returns
    -------
    solution : numpy.ndarray
        Solution to the PDE.
    """
    METHODS = {
        'Euler': euler_step,
        'RK4': rk4_step,
        'Heun': heun_step
    }
    if method not in METHODS:
        raise ValueError('Invalid method: {}. Method must be one of {}.'.format(method, METHODS.keys()))
    else:
        method = METHODS[method]

    A, b, x_array = bvp.construct_matrix()

    u = np.zeros((len(x_array.T), len(t)))

    u[:, 0] = bvp.f_fun(x_array, t[0])
    u[0, :] = bvp.alpha
    u[-1, :] = bvp.beta
    
    if bvp.q_fun is None:
        def PDE(t, u):
            return bvp.C * (A @ u + b)
    else:
        def PDE(t, u, D, A, b):
            return bvp.C * (A @ u + b) + bvp.q_fun(x_array, u)  

    t_ = t[0]
    for n in range(0, len(t)-1):
        t_, u[:, n+1] = euler_step(PDE, t_, u[:, n], 1)
    
    return u


def implicit_euler(bvp, t):
    """
    Function to solve the PDE using the implicit Euler method.

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.

    Returns
    -------
    solution : numpy.ndarray
        Solution to the PDE.
    """
    A, b, x_array = bvp.construct_matrix()

    if bvp.sparse:
        I = sp.eye(bvp.shape)
    else:
        I = np.eye(bvp.shape)

    # Construct left and right sides of equatuiob
    lhs = I - bvp.C * A
    rhs = bvp.C * b

    u = np.zeros((len(x_array), len(t)))
    u[:, 0] = bvp.f_fun(x_array, t[0])

    # Solve for each timestep
    for ti in range(0, len(t)-1):

        if bvp.sparse:
            u[:, ti+1] = sp.linalg.spsolve(lhs, u[:, ti] + rhs)
        else:
            u[:, ti+1] = np.linalg.solve(lhs, u[:, ti] + rhs)

    return u


def crank_nicolson(bvp, t):
    """
    Function to solve the PDE using the Crank-Nicolson method.

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.

    Returns
    -------
    solution : numpy.ndarray
        Solution to the PDE.
    """
    A, b, x_array = bvp.construct_matrix()

    if bvp.sparse:
        I = sp.eye(bvp.shape)
    else:
        I = np.eye(bvp.shape)


    lhs = I - bvp.C * A / 2
    rhs = I + bvp.C * A / 2

    u = np.zeros((len(x_array), len(t)))
    u[:, 0] = bvp.f_fun(x_array, t[0])

    for ti in range(0, len(t)-1):
        if bvp.sparse:
            u[:, ti+1] = sp.linalg.spsolve(lhs, rhs @ u[:, ti] + bvp.C * b)
        else:
            u[:, ti+1] = np.linalg.solve(lhs, rhs @ u[:, ti] + bvp.C * b)

    return u


def imex_euler(bvp, t):
    """
    Function to solve the PDE using the IMEX Euler method.

    Parameters
    ----------
    bvp : BVP object
        Boundary value problem to solve. Object instantiated in SciComp/bvp.py.
    t : numpy.ndarray
        Array of time values.

    Returns
    -------
    solution : numpy.ndarray
        Solution to the PDE.
    """
    A, b, x_array = bvp.construct_matrix()

    I = np.eye(bvp.shape)

    # Construct left and right sides of the equation for the implicit part (diffusive terms)
    lhs = I - bvp.C * A
    rhs = bvp.C * b

    u = np.zeros((len(x_array), len(t)))
    u[:, 0] = bvp.f_fun(x_array, t[0])

    # Solve for each timestep
    for ti in range(0, len(t)-1):
        # Implicit part (diffusive terms)
        u[:, ti+1] = np.linalg.solve(lhs, u[:, ti] + rhs)

        # Explicit part (nonlinear terms)
        if bvp.q_fun is not None:
            u[:, ti+1] += bvp.q_fun(x_array, t[ti], u[:, ti])

    return u