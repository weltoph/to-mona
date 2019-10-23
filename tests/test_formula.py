import unittest

from formula import *

class FormulaTest(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x')
        self.y = Variable('y')
        self.succ_x = Successor(self.x)
        self.x_equal_y = Equal(self.x, self.y)
        self.x_equal_x = Equal(self.x, self.x)
        self.y_equal_y = Equal(self.y, self.y)
        self.port_x = Port("port", self.x)
        self.port_succ_x = Port("port", self.succ_x)
        self.port_y = Port("port", self.y)
        self.guard_x = Guard([self.x_equal_x])
        self.guard_y = Guard([self.y_equal_y])
        self.guard_xy = Guard([self.x_equal_x, self.y_equal_y])

    def test_variables_in_guard(self):
        guard = Guard([self.x_equal_y, self.x_equal_x])
        self.assertEqual(guard.variables, {self.x, self.y})

    def test_consistency_broadcast(self):
        try:
            Broadcast(self.x, self.guard_x, self.port_x)
        except:
            self.fail("unexpected raise of Exception on creation of Broadcast")
        with self.assertRaises(FormulaError):
            Broadcast(self.x, self.guard_y, self.port_y)

    def test_free_variables_broadcast(self):
        b = Broadcast(self.x, self.guard_xy, self.port_succ_x)
        self.assertEqual(b.free_variables, {self.y})

if __name__ == '__main__':
    unittest.main()
