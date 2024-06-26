from scipy.optimize import fsolve
import numpy as np
import warnings

from SciComp._ode_solvers import *

# Custom exceptions
class InputError(Exception):
    """Exception raised for errors in the input."""
    pass

class FunctionError(Exception):
    """Exception raised for errors in the function."""
    pass


def solve_ode(fun, t0, y0, tf=None, n_max=None, method='RK4', deltat_max=0.01, args=None):
    """Solve an ordinary differential equation.

    parameters
    ----------
    fun : function
        Function f(t, y) to integrate. Must return a numpy array.
    t0 : float | int
        Initial value of t.
    y0 : array
        Initial value of y. Must be a numpy array.
    tf : float, optional
        Maximum value of t. If None, n_max must be given. Must be greater than t0.
    n_max : int, optional
        Maximum number of steps. If None, tf must be given. Must be greater than 0.
    method : str, optional
        Integration method. Must be 'Euler' or 'RK4'.
    deltat_max : float, optional
        Maximum step size.
    args : tuple, optional
        Additional arguments to pass to fun. 

    returns
    -------
    t : array
        Array of t values.
    y : array
        Array of y values.

    examples
    --------
    >>> import numpy as np

    >>> def fun(t, y):
    ...     y_ = y[0]
    ...     x_ = y[1]
    ...     return np.array([x_, -y_])
    >>> t0 = 0
    >>> y0 = np.array([1, 0])
    >>> tf = 20
    >>> deltat_max = 0.1

    >>> t, y = solve_ode(fun, t0, y0, tf=tf, method='Euler', deltat_max=deltat_max)
    """
    # ----------------------- Error checking ----------------------- #
    # args checks
    if args is not None:
        # Wrap the fun in lambdas to pass through additional parameters.
        try:
            _ = [*(args)]
        except TypeError as exp:
            suggestion_tuple = (
                "Supplied 'args' cannot be unpacked. Please supply `args`"
                f" as a tuple (e.g. `args=({args},)`)"
            )
            raise TypeError(suggestion_tuple) from exp

        fun = lambda t, x, fun=fun: fun(t, x, *args)
    
    try:
        array = fun(t0, y0)
    except Exception as exp:
        raise FunctionError('ODE function must be of the form f(t, y).') from exp
    
    # t0 checks
    if type(t0) != float and type(t0) != int:
        raise ValueError('Initial value t0 must be a float or int.')
    
    # y0 checks
    if type(y0) != np.ndarray:
        raise InputError('Initial value y0 must a numpy array.')
    elif type(array) != np.ndarray:
        raise FunctionError('ODE function must return a numpy array.')
    elif y0.shape != array.shape:
        raise FunctionError('ODE function must return a numpy array of the same shape as y0. y0.shape: {}. f(t0, y0).shape: {}'.format(y0.shape, array.shape))

    # method checks
    METHODS = {'Euler': euler_step, 'RK4': rk4_step, 'Heun': heun_step}
    if method not in METHODS:
        raise ValueError('Invalid method: {}. Method must be one of {}.'.format(method, METHODS.keys()))
    else:
        method = METHODS[method]

    # tf and n_max checks
    if tf is None and n_max is None:
        raise ValueError('Either tf or n_max must be given.')
    
    if tf is not None:
        try:
            # Prove that tf is a number
            tf + 1 / 1

            if tf <= t0:
                raise ValueError('tf must be greater than t0.')
            
            if tf < 0.001 and method == rk4_step.__name__:
                warnings.warn('A step size ({}) of less than 0.001 is not recommended for the RK4 method. Possible rounding errors may occur.'.format(h))

        except TypeError:
            raise ValueError('tf must be a float or int. Value given: {}. Type: {}'.format(tf, type(tf)))

    if n_max is not None:
        if type(n_max) == int:
            if n_max <= 0:
                raise ValueError('n_max must be greater than 0.')
        else:
            raise ValueError('n_max must be an int.')

    # deltat_max checks
    if type(deltat_max) != float and type(deltat_max) != int:
        raise ValueError('deltat_max must be a float or int.')
    elif deltat_max <= 0:
        raise ValueError('deltat_max must be greater than 0.')

    t = t0
    y = y0
    t_array = [t]
    y_array = [y]
    step = 0

    while (tf is None or t < tf) and (n_max is None or step < n_max):
        t, y = method(fun, t, y, deltat_max)
        t_array.append(t)
        y_array.append(y)
        step += 1

        # Prevent overshooting tf
        if tf is not None and t + deltat_max > tf:
            deltat_max = tf - t

    return np.array(t_array), np.array(y_array)


def shooting(U0, ode, phase_function, ode_solver=solve_ode, root_solver=fsolve, atol=1e-8, function_args=None):
    '''
    Shooting method for solving boundary value problems. 
    
    parameters
    ----------
    U0: array
        The initial guess, U0 should be a list of the form [y0, y1, ..., yn, T], where y0, y1, ..., yn
        are the initial conditions for the ODE and T is the time period for the ODE.
    ode: function
        The ODE to be solved. The function should take the form f(t, y, *args), where t is the
        independent variable, y is the dependent variable, and *args are the parameters of the ODE.
    phase_function: function
        The phase function for the ODE. The function should take the same inputs as the ODE. The phase
        function is used to determine the differential at the start of the ODE and should be zero at
        the end of the ODE.
    ode_solver: function, optional
        The ODE solver to be used. The solver should take the form solver(ode, t0, y0, tf, *args), where
        ode is the ODE to be solved, t0 is the initial time, y0 is the initial condition, tf is the
        final time, and *args are the parameters of the ODE. The default value is solve_ode.
    root_solver: function, optional
        The optimization solver to be used. The solver should take the form solver(fun, x0), where
        fun is the function to be minimized and x0 is the initial guess.
    atol: float, optional
        The absolute tolerance for the ODE solver. The default value is 1e-4.
    function_args: tuple, optional
        Additional parameters to be passed to the ODE. The default value is None. Must be the same 
        parameters for both the ODE and the phase function.

    returns
    -------
    X0: array
        The array of initial conditions for the ODE that satisfy the boundary conditions.
    T: float
        The time period for the ODE.

    example
    -------
    >>> def ode(t, y, a=1, d=0.1, b=0.1):
    ...     x = y[0]
    ...     y = y[1]
    ...     dxdt = x*(1-x) - (a*x*y)/(d+x)
    ...     dydt = b*y*(1 - y/x)
    ...     return np.array([dxdt, dydt])
    >>> def phase_function(t, y):
    ...     dx, dy = ode(t, y)
    ...     return dx
    >>> U0 = [0.6, 0.8, 35]
    >>> X0, T = shooting(U0, ode, phase_function)
    '''
    # Check that the initial guess is of the correct form for the ODE
    try:
        solve_ode(ode, 0, U0[:-1], n_max=1, args=function_args)
    except:
        message = """The initial guess, U0, is not of the correct form. The initial guess should be a 
        list of the form [y0, y1, ..., yn, T], where y0, y1, ..., yn are the initial conditions 
        for the ODE and T is the time period. Values given: U0 = {}""".format(U0)
        raise InputError(message)

    # args checks
    if function_args is not None:
        # Wrap the phase_function in lambdas to pass through additional parameters.
        try:
            _ = [*(function_args)]
        except TypeError as exp:
            suggestion_tuple = (
                "Supplied 'function_args' cannot be unpacked. Please supply `function_args`"
                f" as a tuple (e.g. `function_args=({function_args},)`)"
            )
            raise TypeError(suggestion_tuple) from exp

        phase_function = lambda t, x, phase_function=phase_function: phase_function(t, x, *function_args)

    try:
        # TypeError: Value after * must be an iterable, not NoneType
        phase_function(0, U0[:-1])
    except:
        message = """The phase function is not of the correct form. The phase function should take 
        the same inputs as the ODE. Input provided for U0 = {}""".format(U0)
        raise FunctionError(message)
    
    # TODO: Checks for the ODE solver and root solver
    # Tests

    # Set up function to optimize
    def shooting_root(initial_guess):
        T = initial_guess[-1]
        Y0 = np.array(initial_guess[:-1])

        # Solve the ODE
        t, y = ode_solver(ode, 0, Y0, tf=T, args=function_args)

        # Set up the conditions array
        num_vars = len(initial_guess)
        conditions = np.zeros(num_vars)
        # Dynamically fill in the conditions array
        for i in range(num_vars - 1):
            conditions[i] = y[-1,i] - Y0[i]        # X(T) - X(0) = 0

        # Final condition is the phase function
        phase_value = phase_function(0, Y0)
        conditions[-1] = phase_value               # dx/dt(T) = 0

        return conditions

    # TODO: Implement a better root finding algorithm, e.g. particle swarm optimization
    sol = root_solver(shooting_root, U0)
    X0 = np.array(sol[:-1])
    T = sol[-1]

    # Check that the solution is valid. 
    final_conditions = shooting_root(sol)
    if not np.allclose(final_conditions, np.zeros(len(sol)), atol=atol):
        message = '''The solution does not satisfy the boundary conditions. 
        The final conditions are: {}. 
        The final value of X0 and T is: {}, {}. 
        the initial guess or increasing the absolute tolerance.
        '''.format(final_conditions, X0, T)
        raise ValueError(message)
    
    if T <= 0:
        raise ValueError('The time period is not positive. Please try a different initial guess.')

    return X0, T

